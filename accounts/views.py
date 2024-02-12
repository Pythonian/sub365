import logging
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

import requests
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from requests.exceptions import RequestException
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .decorators import (
    onboarding_completed,
    redirect_authenticated_user,
    stripe_onboarding_required,
)
from .forms import (
    CoinPaymentDetailForm,
    CoinpaymentsOnboardingForm,
    CoinPlanForm,
    OnboardingForm,
    StripePaymentDetailForm,
    StripePlanForm,
)
from .models import (
    Affiliate,
    AffiliateInvitee,
    AffiliatePayment,
    CoinPlan,
    CoinSubscription,
    Server,
    ServerOwner,
    StripePlan,
    StripeSubscription,
    Subscriber,
    User,
)
from .tasks import check_coin_transaction_status, send_affiliate_email
from .utils import create_hmac_signature, mk_paginator

discord_oauth2_authorization_url = "https://discord.com/api/oauth2/authorize"

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_API_KEY

PAGINATION_ITEMS = 12


def index(request):
    return render(request, "index.html")


@redirect_authenticated_user
def discord_login(request):
    """View for initiating Discord OAuth2 authentication."""

    # Generate a random state value for CSRF protection
    state = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(32))

    # Store the generated state value in the session for later use
    request.session["discord_oauth_state"] = state

    # Build the URL path the user will be redirected to after authentication
    redirect_uri = request.build_absolute_uri(reverse("discord_callback"))

    # Construct the Discord OAuth2 authorization URL
    authorization_url = f"{discord_oauth2_authorization_url}?client_id={settings.DISCORD_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=identify+email+connections+guilds&state={state}"

    return redirect(authorization_url)


@redirect_authenticated_user
def subscribe_redirect(request):
    """View for redirecting a new subscriber to Discord OAuth2 for authentication."""

    # Get the referral name from the query parameters
    referral = request.GET.get("ref")

    # Store the referral name in the session for later use
    request.session["referral_redirect"] = referral

    # Build the URL path the user will be redirected to after authentication
    redirect_uri = request.build_absolute_uri(reverse("discord_callback"))

    # Construct the Discord OAuth2 authorization URL
    authorization_url = f"{discord_oauth2_authorization_url}?client_id={settings.DISCORD_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=identify+email&state=subscriber&referral={referral}"

    return redirect(authorization_url)


@redirect_authenticated_user
def discord_callback(request):
    """Handles the callback URL for Discord OAuth authorization."""
    # Retrieve values from the URL parameters
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Retrieve values stored in the session
    referral = request.session.get("referral_redirect")
    stored_state = request.session.get("discord_oauth_state")

    # Check if the state parameter matches the stored state value
    if stored_state and state != stored_state:
        messages.error(request, "An error occured. Your discord authorization was aborted.")
        del request.session["discord_oauth_state"]
        return redirect("index")

    if code:
        # Prepare the payload for the token request
        redirect_uri = request.build_absolute_uri(reverse("discord_callback"))
        payload = {
            "client_id": settings.DISCORD_CLIENT_ID,
            "client_secret": settings.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": "email identify connections guilds",
        }

        # Make the POST request to obtain the access token
        token_url = "https://discord.com/api/oauth2/token"
        response = requests.post(token_url, data=payload)

        if response.status_code == 200:
            access_token = response.json().get("access_token")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            response = requests.get("https://discord.com/api/users/@me", headers=headers)
            if response.status_code == 200:
                # Get the user information from the response
                user_info = response.json()
                # This user is registering via a referral link
                if state == "subscriber":
                    try:
                        # Check if the user already exists
                        user = User.objects.get(username=user_info["username"])
                    except User.DoesNotExist:
                        # Create a new user as a subscriber
                        user = User.objects.create_user(
                            username=user_info["username"],
                            is_subscriber=True,
                        )
                        # Update the subscriber object created by the signal for the user.
                        subscriber = Subscriber.objects.get(user=user)
                        subscriber.discord_id = user_info.get("id")
                        subscriber.username = user_info.get("username")
                        subscriber.avatar = user_info.get("avatar", "")
                        subscriber.email = user_info.get("email")
                        subscriber.save()
                        # Connect the subscriber to the referring serverowner
                        serverowner = ServerOwner.objects.get(subdomain=referral)
                        subscriber.subscribed_via = serverowner
                        subscriber.save()
                    login(request, user)
                    return redirect("dashboard_view")
                else:
                    # This is a serverowner
                    guild_response = requests.get("https://discord.com/api/users/@me/guilds", headers=headers)
                    if guild_response.status_code == 200:
                        # Gets all the discord servers joined by the user
                        server_list = guild_response.json()
                        # Process the server list to only return servers owned by user
                        owned_servers = []
                        if server_list:
                            for server in server_list:
                                server_id = server["id"]
                                server_name = server["name"]
                                server_icon = server.get("icon", "")
                                serverowner = server["owner"]
                                # Check if the user owns the server
                                if serverowner:
                                    owned_servers.append(
                                        {"id": server_id, "name": server_name, "icon": server_icon},
                                    )
                    else:
                        # Redirect user and show a message to create a server
                        messages.info(
                            request,
                            "You do not have any servers. Please create a server on Discord before continuing.",
                        )
                        return redirect("index")

                    try:
                        # Check if a user already exists
                        user = User.objects.get(username=user_info["username"])
                    except User.DoesNotExist:
                        # Create a new user as a serverowner
                        user = User.objects.create_user(
                            username=user_info["username"],
                            is_serverowner=True,
                        )
                        # Update the serverowner object created by the signal
                        serverowner = ServerOwner.objects.get(user=user)
                        serverowner.discord_id = user_info.get("id")
                        serverowner.username = user_info.get("username")
                        serverowner.avatar = user_info.get("avatar", "")
                        serverowner.email = user_info.get("email")
                        serverowner.save()
                        # Save server objects associated with the serverowner
                        for server in owned_servers:
                            owner_server = Server.objects.create(owner=serverowner)
                            owner_server.server_id = server["id"]
                            owner_server.name = server["name"]
                            owner_server.icon = server["icon"]
                            owner_server.save()
                    login(request, user)
                    return redirect("dashboard_view")
            else:
                messages.error(request, "Failed to obtain user information from Discord.")
                return redirect("index")
        else:
            messages.error(request, "Failed to obtain access token.")
            return redirect("index")

    messages.error(request, "Your discord authorization was aborted.")
    return redirect("index")


@login_required
def onboarding(request):
    """Handle the onboarding of a Serverowner."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    if serverowner.stripe_account_id and not serverowner.stripe_onboarding:
        return redirect("collect_user_info")
    elif serverowner.stripe_onboarding or serverowner.coinpayment_onboarding:
        return redirect("dashboard")

    if request.method == "POST":
        form = OnboardingForm(request.POST, user=request.user)
        if form.is_valid():
            # Check which button was clicked and set the appropriate session data
            if "connect_stripe" in request.POST:
                form.save(user=request.user)
                return redirect("create_stripe_account")
            elif "connect_coinbase" in request.POST:
                form.save(user=request.user)
                # Set the session variable to indicate the user clicked "connect_coinbase"
                request.session["coinbase_onboarding"] = True
                return redirect("onboarding_crypto")
    else:
        form = OnboardingForm(user=request.user)

    # Check if the session variable indicates a previous "connect_coinbase" click
    if request.session.get("coinbase_onboarding"):
        # If so, check if coinpayment_onboarding is False, then redirect
        if not serverowner.coinpayment_onboarding:
            return redirect("onboarding_crypto")
        # Clear the session variable
        del request.session["coinbase_onboarding"]

    template = "account/onboarding.html"
    context = {
        "form": form,
    }

    return render(request, template, context)


@login_required
def onboarding_crypto(request):
    """Handle the onboarding process for connecting with coinpayment."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    try:
        if serverowner.coinpayment_onboarding:
            return redirect("dashboard")
    except ObjectDoesNotExist:
        messages.error(request, "You have trespassed into forbidden territory.")
        return redirect("index")

    if serverowner.stripe_account_id:
        if serverowner.stripe_onboarding:
            return redirect("dashboard")
        return redirect("collect_user_info")

    if request.method == "POST":
        form = CoinpaymentsOnboardingForm(request.POST)
        if form.is_valid():
            # Get the API keys entered by the user
            api_secret_key = form.cleaned_data["coinpayment_api_secret_key"]
            api_public_key = form.cleaned_data["coinpayment_api_public_key"]
            try:
                # Make the API request to verify the coinpayment API keys
                endpoint = "https://www.coinpayments.net/api.php"
                data = f"version=1&cmd=get_basic_info&key={api_public_key}&format=json"
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "HMAC": create_hmac_signature(data, api_secret_key),
                }
                response = requests.post(endpoint, data=data, headers=headers)
                response.raise_for_status()
                result = response.json()["result"]
                if result:
                    serverowner.coinpayment_api_secret_key = api_secret_key
                    serverowner.coinpayment_api_public_key = api_public_key
                    serverowner.coinpayment_onboarding = True
                    serverowner.save()
                    return redirect("dashboard_view")
                else:
                    form.add_error(None, "Invalid Coinbase API keys.")
            except RequestException as e:
                # RequestException includes issues like network errors, invalid responses etc.
                msg = f"Failed to verify Coinbase API keys: {e}"
                logger.exception(msg)
                form.add_error(None, "Failed to verify Coinbase API keys. Please try again.")
            except ValueError as e:
                # Raised if there is an issue with parsing JSON response
                msg = f"Failed to verify Coinbase API keys: {e}"
                logger.exception(msg)
                form.add_error(None, "Failed to parse API response. Please try again.")
            except Exception as e:
                # Catch any other unexpected exceptions and log them
                msg = f"An unexpected error occurred: {e}"
                logger.exception(msg)
                form.add_error(None, "An unexpected error occurred. Please try again later.")
    else:
        form = CoinpaymentsOnboardingForm()

    template = "account/onboarding_crypto.html"
    context = {
        "form": form,
    }

    return render(request, template, context)


@login_required
def dashboard_view(request):
    """Redirect the user to the appropriate dashboard."""
    user = request.user
    if user.is_serverowner:
        if not user.serverowner.subdomain:
            return redirect("onboarding")
        return redirect("dashboard")
    elif user.is_affiliate:
        return redirect("affiliate_dashboard")
    elif user.is_subscriber and not user.is_affiliate:
        return redirect("subscriber_dashboard")
    else:
        messages.info(request, "You don't have the permission to access that. Please logout and retry.")
        return redirect("index")


@login_required
@stripe_onboarding_required
def create_stripe_account(request):
    """Create a Stripe account for the user."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    connected_account = stripe.Account.create(
        type="standard",
        email=serverowner.email,
    )

    # Retrieve the created Stripe account ID
    stripe_account_id = connected_account.id

    # Update the Stripe account ID for the current user
    serverowner.stripe_account_id = stripe_account_id
    serverowner.save()

    return redirect("collect_user_info")


@login_required
@stripe_onboarding_required
def collect_user_info(request):
    """Collect additional user info for Stripe onboarding."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    # Generate an account link for the onboarding process
    account_link = stripe.AccountLink.create(
        account=serverowner.stripe_account_id,
        refresh_url=request.build_absolute_uri(reverse("stripe_refresh")),
        return_url=request.build_absolute_uri(reverse("dashboard")),
        type="account_onboarding",
    )

    # Redirect the user to the Stripe onboarding flow
    return redirect(account_link.url)


@login_required
@stripe_onboarding_required
def stripe_refresh(request):
    """Handle refreshing the Stripe account information."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    # Retrieve the Stripe account ID from the request or the Stripe API response
    stripe_account_id = request.GET.get("account_id")

    # Update the profile's stripe_account_id field
    serverowner.stripe_account_id = stripe_account_id
    serverowner.save()

    # Redirect the user to the onboarding process
    return redirect("collect_user_info")


@login_required
@require_POST
def delete_account(request):
    """View to delete account during onboarding process."""
    request.user.delete()
    messages.success(request, "Your account has been deleted.")
    return LogoutView.as_view()(request)


##################################################
#                   SERVEROWNERS                 #
##################################################


@login_required
@onboarding_completed
def dashboard(request):
    """View for rendering the serverowner's dashboard."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    template = "serverowner/dashboard.html"
    context = {
        "serverowner": serverowner,
        "discord_client_id": settings.DISCORD_CLIENT_ID,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def plans(request):
    """View to display a serverowner's plans and handle new plan creation."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    coinpayment_onboarding = serverowner.coinpayment_onboarding

    if request.method == "POST":
        form = CoinPlanForm(request.POST) if coinpayment_onboarding else StripePlanForm(request.POST)

        if form.is_valid():
            try:
                if coinpayment_onboarding:
                    coin_plan = form.save(commit=False)
                    coin_plan.serverowner = serverowner
                    coin_plan.save()
                else:
                    interval_count = form.cleaned_data["interval_count"]
                    # Create a product on Stripe
                    product = stripe.Product.create(
                        name=form.cleaned_data["name"],
                        description=form.cleaned_data["description"],
                        active=True,
                    )
                    # Create a price for the product
                    price = stripe.Price.create(
                        product=product.id,
                        unit_amount=int(form.cleaned_data["amount"] * 100),
                        currency="usd",
                        recurring={
                            "interval": "month",
                            "interval_count": interval_count,
                        },
                    )
                    stripe_product = form.save(commit=False)
                    stripe_product.price_id = price.id
                    stripe_product.product_id = product.id
                    stripe_product.serverowner = serverowner
                    stripe_product.save()

                messages.success(request, "Your Subscription Plan has been successfully created.")
                return redirect("plans")
            except stripe.error.StripeError as e:
                logger.exception("An error occurred during a Stripe API call: %s", str(e))
                messages.error(request, "An error occurred while processing your request. Please try again later.")
        else:
            messages.error(request, "An error occurred while creating your Plan. Please try again.")
    else:
        form = CoinPlanForm() if coinpayment_onboarding else StripePlanForm()

    plans = serverowner.get_plans()
    plans = mk_paginator(request, plans, PAGINATION_ITEMS)

    template = "serverowner/plans/list.html"
    context = {
        "serverowner": serverowner,
        "form": form,
        "plans": plans,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def plan_detail(request, plan_id):
    """View to display detailed information about a specific plan."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    coinpayment_onboarding = serverowner.coinpayment_onboarding

    PlanModel = CoinPlan if coinpayment_onboarding else StripePlan
    plan = get_object_or_404(PlanModel, id=plan_id, serverowner=serverowner)
    subscribers = plan.get_plan_subscribers()
    subscribers = mk_paginator(request, subscribers, PAGINATION_ITEMS)

    FormClass = CoinPlanForm if coinpayment_onboarding else StripePlanForm

    if request.method == "POST":
        form = FormClass(request.POST, instance=plan)
        if form.is_valid():
            if coinpayment_onboarding:
                plan = form.save()
                messages.success(request, "Your Subscription Plan has been successfully updated.")
                return redirect(plan)
            else:
                try:
                    with transaction.atomic():
                        # Update the product on Stripe
                        product_params = {
                            "name": form.cleaned_data["name"],
                            "description": form.cleaned_data["description"],
                            "active": True,
                        }
                        stripe.Product.modify(plan.product_id, **product_params)
                        # Save the updated plan details in the database
                        plan = form.save()
                        messages.success(request, "Your Subscription Plan has been successfully updated.")
                        return redirect(plan)
                except stripe.error.StripeError as e:
                    msg = f"An error occurred during a Stripe API call: {e}"
                    logger.exception(msg)
                    messages.error(
                        request,
                        "An error occurred while processing your request. Please try again later.",
                    )
        else:
            messages.error(request, "An error occurred while updating your Plan. Please try again.")
    else:
        form = FormClass(instance=plan)

    template = "serverowner/plans/detail.html"
    context = {
        "plan": plan,
        "form": form,
        "subscribers": subscribers,
    }

    return render(request, template, context)


@login_required
@require_POST
def deactivate_plan(request):
    """View to handle the deactivation of a plan."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    try:
        PlanModel = CoinPlan if serverowner.coinpayment_onboarding else StripePlan

        if request.method == "POST":
            product_id = request.POST.get("product_id")
            plan = get_object_or_404(PlanModel, id=product_id, serverowner=serverowner)

            if serverowner.coinpayment_onboarding:
                # Update the plan status in the database
                plan.status = CoinPlan.PlanStatus.INACTIVE
                plan.save()
                messages.success(request, "Your plan has been successfully deactivated.")
            else:
                try:
                    with transaction.atomic():
                        # Retrieve the product ID from the plan's StripePlan object
                        product_id = plan.product_id
                        # Deactivate the product on Stripe
                        stripe.Product.modify(product_id, active=False)
                        # Deactivate the prices associated with the product
                        prices = stripe.Price.list(product=product_id, active=True, limit=100)
                        for price in prices:
                            stripe.Price.modify(price.id, active=False)

                        # Update the plan status in the database
                        plan.status = StripePlan.PlanStatus.INACTIVE
                        plan.save()
                        messages.success(request, "Your plan has been successfully deactivated.")
                except stripe.error.StripeError as e:
                    logger.exception("An error occurred during a Stripe API call: %s", str(e))
                    messages.error(
                        request,
                        "An error occurred while processing your request. Please try again later.",
                    )
        return redirect(plan)
    except Http404:
        messages.error(request, "Plan not found.")
        return redirect("plans")


@login_required
@onboarding_completed
def subscribers(request):
    """Display the subscribers of a serverowner's plans."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    subscribers = serverowner.get_subscribed_users()
    subscribers = mk_paginator(request, subscribers, PAGINATION_ITEMS)

    template = "serverowner/subscribers/list.html"
    context = {
        "serverowner": serverowner,
        "subscribers": subscribers,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def subscriber_detail(request, subscriber_id):
    """View to display information about a subscriber."""
    subscriber = get_object_or_404(Subscriber, id=subscriber_id)
    subscriptions = subscriber.get_subscriptions()
    subscriptions = mk_paginator(request, subscriptions, PAGINATION_ITEMS)

    SubscriptionModel = CoinSubscription if request.user.serverowner.coinpayment_onboarding else StripeSubscription

    try:
        # Retrieve the latest active subscription for the subscriber
        subscription = SubscriptionModel.active_subscriptions.filter(
            subscriber=subscriber,
        ).latest()
    except SubscriptionModel.DoesNotExist:
        subscription = None

    template = "serverowner/subscribers/detail.html"
    context = {
        "subscriber": subscriber,
        "subscription": subscription,
        "subscriptions": subscriptions,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def affiliates(request):
    """Display a list of affiliates associated with the serverowner."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    affiliates = Affiliate.objects.filter(serverowner=serverowner)
    affiliates = mk_paginator(request, affiliates, PAGINATION_ITEMS)

    template = "serverowner/affiliate/list.html"
    context = {
        "serverowner": serverowner,
        "affiliates": affiliates,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def affiliate_detail(request, subscriber_id):
    """Display information about an affiliate and their invitees."""
    subscriber = get_object_or_404(Subscriber, id=subscriber_id)
    affiliate = get_object_or_404(Affiliate, subscriber=subscriber)
    invitations = affiliate.get_affiliate_invitees()
    invitations = mk_paginator(request, invitations, PAGINATION_ITEMS)

    template = "serverowner/affiliate/detail.html"
    context = {
        "affiliate": affiliate,
        "invitations": invitations,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def pending_affiliate_payment(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    affiliates = serverowner.get_pending_affiliates()
    affiliates = mk_paginator(request, affiliates, PAGINATION_ITEMS)

    if serverowner.coinpayment_onboarding:
        if request.method == "POST":
            affiliate_id = request.POST.get("affiliate_id")
            if affiliate_id is not None:
                affiliate = Affiliate.objects.filter(pk=affiliate_id).first()
                if affiliate is not None:
                    try:
                        endpoint = "https://www.coinpayments.net/api.php"
                        data = (
                            f"version=1&cmd=create_withdrawal&amount={affiliate.pending_coin_commissions}&currency="
                            + settings.COINBASE_CURRENCY
                            + f"&add_tx_fee=1&auto_confirm=1&address={affiliate.paymentdetail.litecoin_address}&key={serverowner.coinpayment_api_public_key}&format=json"
                        )
                        headers = {
                            "Content-Type": "application/x-www-form-urlencoded",
                            "HMAC": create_hmac_signature(data, serverowner.coinpayment_api_secret_key),
                        }
                        response = requests.post(endpoint, data=data, headers=headers)
                        response.raise_for_status()
                        result = response.json()["result"]
                        if result.get("status") == 1:
                            affiliate_pending_commission = affiliate.pending_commissions
                            serverowner.total_coin_pending_commissions = (
                                F("total_coin_pending_commissions") - affiliate.pending_coin_commissions
                            )
                            serverowner.total_pending_commissions = (
                                F("total_pending_commissions") - affiliate.pending_commissions
                            )
                            serverowner.save()

                            # Update the affiliate's pending_commissions and total_coin_commissions_paid fields
                            affiliate.total_coin_commissions_paid = (
                                F("total_coin_commissions_paid") + affiliate.pending_coin_commissions
                            )
                            affiliate.total_commissions_paid = (
                                F("total_commissions_paid") + affiliate.pending_commissions
                            )
                            affiliate.pending_coin_commissions = Decimal(0)
                            affiliate.pending_commissions = Decimal(0)
                            affiliate.last_payment_date = timezone.now()
                            affiliate.save()

                            # Mark the associated AffiliatePayment instances as paid
                            affiliate_payments = AffiliatePayment.objects.filter(
                                serverowner=serverowner,
                                affiliate=affiliate,
                                paid=False,
                            )
                            affiliate_payments.update(paid=True, date_payment_confirmed=timezone.now())
                            messages.success(
                                request,
                                "The commission has been sent to the affiliate.",
                            )

                            # Send email to affiliate
                            send_affiliate_email.delay(
                                affiliate.subscriber.email,
                                affiliate.subscriber.username,
                                serverowner.username,
                                affiliate_pending_commission,
                            )

                            return redirect("pending_affiliate_payment")
                        else:
                            # TODO: If withdrawal amount is not enough?
                            msg = f"Withdrawal status: {result.get('status')}"
                            logger.warning(msg)
                    except requests.exceptions.RequestException as e:
                        msg = f"Coinbase API request failed: {e}"
                        logger.exception(msg)
                        messages.error(
                            request,
                            "An error occurred while communicating with Coinbase. Please try again later.",
                        )
                        return redirect("pending_affiliate_payment")
                    except (ValueError, KeyError) as e:
                        msg = f"Failed to parse Coinbase API response: {e}"
                        logger.exception(msg)
                        messages.error(
                            request,
                            "An unexpected error occurred while processing the response. Please try again later.",
                        )
                        return redirect("pending_affiliate_payment")
                    except Exception as e:
                        msg = f"An unexpected error occurred: {e}"
                        logger.exception(msg)
                        messages.error(
                            request,
                            "An unexpected error occurred. Please try again later.",
                        )
                        return redirect("pending_affiliate_payment")
    else:
        if request.method == "POST":
            affiliate_id = request.POST.get("affiliate_id")
            if affiliate_id is not None:
                affiliate = Affiliate.objects.filter(pk=affiliate_id).first()
                if affiliate is not None:
                    affiliate_pending_commission = affiliate.pending_commissions
                    # Update the server owner's total_pending_commissions
                    serverowner.total_pending_commissions = (
                        F("total_pending_commissions") - affiliate.pending_commissions
                    )
                    serverowner.save()

                    # Update the affiliate's pending_commissions and total_commissions_paid fields
                    affiliate.total_commissions_paid = F("total_commissions_paid") + affiliate.pending_commissions
                    affiliate.pending_commissions = Decimal(0)
                    affiliate.last_payment_date = timezone.now()
                    affiliate.save()

                    # Mark the associated AffiliatePayment instances as paid
                    affiliate_payments = AffiliatePayment.objects.filter(
                        serverowner=serverowner,
                        affiliate=affiliate,
                        paid=False,
                    )
                    affiliate_payments.update(paid=True, date_payment_confirmed=timezone.now())

                    messages.success(
                        request,
                        f"You have marked payment of ${affiliate_pending_commission} to {affiliate.subscriber.username} as confirmed.",
                    )
                    return redirect("pending_affiliate_payment")

    template = "serverowner/affiliate/payment_pending.html"
    context = {
        "serverowner": serverowner,
        "affiliates": affiliates,
    }

    return render(request, template, context)


@login_required
@onboarding_completed
def confirmed_affiliate_payment(request):
    """View to list affiliates a serverowner has paid commissions."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    affiliates = serverowner.get_confirmed_affiliate_payments()
    affiliates = mk_paginator(request, affiliates, PAGINATION_ITEMS)

    template = "serverowner/affiliate/payment_confirmed.html"
    context = {
        "serverowner": serverowner,
        "affiliates": affiliates,
    }

    return render(request, template, context)


##################################################
#                   SUBSCRIBERS                  #
##################################################


@login_required
def subscriber_dashboard(request):
    """Render the subscription information of a subscriber."""
    subscriber = get_object_or_404(Subscriber, user=request.user)
    serverowner = subscriber.subscribed_via

    # Retrieve the plans related to the ServerOwner
    plans = (
        CoinPlan.active_plans.filter(serverowner=serverowner)
        if serverowner.coinpayment_onboarding
        else StripePlan.active_plans.filter(serverowner=serverowner)
    )

    SubscriptionModel = CoinSubscription if serverowner.coinpayment_onboarding else StripeSubscription

    try:
        # Retrieve the latest active subscription for the subscriber
        latest_subscription = SubscriptionModel.active_subscriptions.filter(subscriber=subscriber).latest()
    except SubscriptionModel.DoesNotExist:
        latest_subscription = None

    # Retrieve all the subscriptions done by the subscriber
    subscriptions = SubscriptionModel.objects.filter(subscriber=subscriber).exclude(
        status=SubscriptionModel.SubscriptionStatus.PENDING,
    )

    subscriptions = mk_paginator(request, subscriptions, PAGINATION_ITEMS)

    form = CoinPaymentDetailForm() if serverowner.coinpayment_onboarding else StripePaymentDetailForm()

    template = "subscriber/dashboard.html"
    context = {
        "plans": plans,
        "subscriber": subscriber,
        "serverowner": serverowner,
        "subscription": latest_subscription,
        "subscriptions": subscriptions,
        "form": form,
    }

    return render(request, template, context)


@api_view(["GET"])
@login_required
def check_pending_subscription(request):
    try:
        subscriber = Subscriber.objects.get(user=request.user)
        latest_pending_subscription = subscriber.get_latest_pending_subscription()

        if latest_pending_subscription:
            # Return data indicating a pending subscription
            data = {"has_pending_subscription": True}
        else:
            # Return data indicating no pending subscription
            data = {"has_pending_subscription": False}
    except Subscriber.DoesNotExist:
        # Handle the case when there's no Subscriber instance for the user
        data = {"has_pending_subscription": False}

    return Response(data)


@login_required
@require_POST
def subscription_coin(request, plan_id):
    """View for subscribing to a plan using the Coinpayments API."""
    plan = get_object_or_404(CoinPlan, id=plan_id)
    subscriber = get_object_or_404(Subscriber, user=request.user)

    try:
        endpoint = "https://www.coinpayments.net/api.php"
        data = (
            f"version=1&cmd=create_transaction&amount={plan.amount}&currency1=USD&currency2="
            + settings.COINBASE_CURRENCY
            + f"&buyer_email={subscriber.email}&key={subscriber.subscribed_via.coinpayment_api_public_key}&format=json"
        )
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "HMAC": create_hmac_signature(data, subscriber.subscribed_via.coinpayment_api_secret_key),
        }
        response = requests.post(endpoint, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()["result"]
        if result:
            checkout_url = result["checkout_url"]
            CoinSubscription.objects.create(
                subscriber=subscriber,
                subscribed_via=subscriber.subscribed_via,
                plan=plan,
                subscription_id=result["txn_id"],
                coin_amount=result["amount"],
                address=result["address"],
                checkout_url=result["checkout_url"],
                status_url=result["status_url"],
                status=CoinSubscription.SubscriptionStatus.PENDING,
            )
            check_coin_transaction_status.apply_async(
                eta=timezone.now() + timedelta(minutes=1),
            )
            return redirect(checkout_url)
        else:
            messages.error(
                request,
                "An error occurred during the transaction. Please try again later.",
            )
            return redirect("subscriber_dashboard")
    except requests.exceptions.RequestException as e:
        logger.exception(f"Coinbase API request failed: {e}")
        messages.error(
            request,
            "An error occurred while communicating with Coinbase. Please try again later.",
        )
        return redirect("subscriber_dashboard")
    except (ValueError, KeyError) as e:
        logger.exception(f"Failed to parse Coinbase API response: {e}")
        messages.error(
            request,
            "An unexpected error occurred while processing the response. Please try again later.",
        )
        return redirect("subscriber_dashboard")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        messages.error(request, "An unexpected error occurred. Please try again later.")
        return redirect("subscriber_dashboard")


@login_required
@require_POST
def subscription_stripe(request, plan_id):
    """View for subscribing to a plan using the Stripe Checkout API."""
    plan = get_object_or_404(StripePlan, id=plan_id)
    subscriber = get_object_or_404(Subscriber, user=request.user)

    session_data = {
        "success_url": request.build_absolute_uri(reverse("subscription_success"))
        + f"?session_id={{CHECKOUT_SESSION_ID}}&subscribed_plan={plan.id}",
        "cancel_url": request.build_absolute_uri(reverse("subscriber_dashboard")),
        "payment_method_types": ["card"],
        "line_items": [
            {
                "price": plan.price_id,
                "quantity": 1,
            },
        ],
        "mode": "subscription",
        "subscription_data": {
            "transfer_data": {
                "destination": subscriber.subscribed_via.stripe_account_id,
                "amount_percent": 100,
            },
        },
    }

    try:
        if subscriber.stripe_customer_id:
            session_data["customer"] = subscriber.stripe_customer_id
        else:
            session_data["customer_email"] = subscriber.email
        session = stripe.checkout.Session.create(**session_data)
    except stripe.error.StripeError as e:
        logger.exception(f"Stripe API Error: {e}")
        messages.error(
            request,
            "An error occurred while processing your request. Please try again later.",
        )
        return redirect("subscriber_dashboard")

    return redirect(session.url)


@login_required
def subscription_success(request):
    if request.method == "GET" and request.GET.get("session_id"):
        subscriber = get_object_or_404(Subscriber, user=request.user)
        subscription = None
        try:
            session_id = request.GET.get("session_id")
            plan_id = request.GET.get("subscribed_plan")
            plan = get_object_or_404(StripePlan, id=plan_id)

            if StripeSubscription.objects.filter(session_id=session_id).exists():
                messages.info(request, "You have already subscribed to this plan.")
                return redirect("subscriber_dashboard")

            session_info = stripe.checkout.Session.retrieve(session_id)

            subscription_id = session_info.subscription
            subscription_info = stripe.Subscription.retrieve(subscription_id)

            # Extract the dates directly from Stripe API response
            subscription_date = datetime.fromtimestamp(session_info.created, tz=timezone.utc)
            current_period_end = subscription_info.current_period_end
            expiration_date = datetime.fromtimestamp(current_period_end, tz=timezone.utc)

            subscription = StripeSubscription.objects.create(
                subscriber=subscriber,
                subscribed_via=subscriber.subscribed_via,
                plan=plan,
                subscription_date=subscription_date,
                expiration_date=expiration_date,
                subscription_id=subscription_id,
                session_id=session_id,
                status=StripeSubscription.SubscriptionStatus.ACTIVE,
            )

            # Save the customer ID to the subscriber
            subscriber.stripe_customer_id = session_info.customer
            subscriber.save()

            # Handle affiliate logic
            try:
                affiliateinvitee = AffiliateInvitee.objects.get(invitee_discord_id=subscriber.discord_id)
                AffiliatePayment.objects.create(
                    serverowner=subscriber.subscribed_via,
                    affiliate=affiliateinvitee.affiliate,
                    subscriber=subscriber,
                    amount=affiliateinvitee.get_affiliate_commission_payment(),
                )

                # TODO: affiliateinvitee.affiliate.update_last_payment_date()
                affiliateinvitee.affiliate.pending_commissions = (
                    F("pending_commissions") + affiliateinvitee.get_affiliate_commission_payment()
                )
                affiliateinvitee.affiliate.save()

                subscriber.subscribed_via.total_pending_commissions = (
                    F("total_pending_commissions") + affiliateinvitee.get_affiliate_commission_payment()
                )
                subscriber.subscribed_via.save()

            except ObjectDoesNotExist:
                affiliateinvitee = None

            # Increment the subscriber count for the plan
            plan.subscriber_count = F("subscriber_count") + 1
            plan.save()

        except stripe.error.StripeError as e:
            logger.exception(f"Stripe Session retrieval error: {e}")
            messages.error(request, "An error occurred during the subscription process. Please try again.")
            return redirect("subscriber_dashboard")

        except Http404:
            messages.error(request, "Invalid subscription data. Please try again.")
            return redirect("subscriber_dashboard")

    else:
        return redirect("subscriber_dashboard")

    template = "subscriber/success.html"
    context = {
        "subscription": subscription,
    }

    return render(request, template, context)


@login_required
@require_POST
def subscription_cancel(request):
    """View to handle the subscription cancellation for a subscriber."""
    subscriber = get_object_or_404(Subscriber, user=request.user)

    if subscriber.subscribed_via.coinpayment_onboarding:
        try:
            coin_subscription = get_object_or_404(
                CoinSubscription,
                subscriber=subscriber,
                status=CoinSubscription.SubscriptionStatus.ACTIVE,
            )
            coin_subscription.status = CoinSubscription.SubscriptionStatus.CANCELED
            coin_subscription.save()
            messages.success(
                request,
                f"Your subscription has been canceled successfully. It will not be renewed when it expires on {coin_subscription.expiration_date.strftime('%B %d, %Y')}",
            )
        except Http404:
            # If the subscription is not found, it will raise a 404 error with a message
            messages.error(request, "No active subscription found for cancellation.")
        except Exception as e:
            msg = f"An unexpected error occurred: {e}"
            logger.exception(msg)
            messages.error(
                request,
                "An unexpected error occurred while processing your request. Please try again later.",
            )
    else:
        try:
            with transaction.atomic():
                # Retrieve the active subscription for the subscriber
                subscription = get_object_or_404(
                    StripeSubscription,
                    subscriber=subscriber,
                    status=StripeSubscription.SubscriptionStatus.ACTIVE,
                )

                # Cancel the subscription at the end of the billing period
                subscription_stripe = stripe.Subscription.retrieve(subscription.subscription_id)
                subscription_stripe.cancel_at_period_end = True
                subscription_stripe.save()
                # Update the Subscription object
                subscription.status = StripeSubscription.SubscriptionStatus.CANCELED
                subscription.save()

                messages.success(
                    request,
                    f"Your subscription has been canceled successfully. It will not be renewed when it expires on {subscription.expiration_date.strftime('%B %d, %Y')}",
                )
        except stripe.error.StripeError as e:
            msg = f"An error occurred during a Stripe API call: {e}"
            logger.exception(msg)
            messages.error(
                request,
                "An error occurred while canceling your subscription. Please try again later.",
            )

        except Http404:
            # If the subscription is not found, it will raise a 404 error with a message
            messages.error(request, "No active subscription found for cancellation.")

        except Exception as e:
            msg = f"An unexpected error occurred: {e}"
            logger.exception(msg)
            messages.error(
                request,
                "An unexpected error occurred while processing your request. Please try again later.",
            )

    return redirect("subscriber_dashboard")


@login_required
@require_POST
def affiliate_upgrade(request):
    """Handle the upgrading of a subscriber to an affiliate."""
    subscriber = get_object_or_404(Subscriber, user=request.user)

    # Check if the subscriber already has an affiliate object
    if hasattr(subscriber, "affiliate"):
        # Subscriber is already an affiliate, redirect to affiliate dashboard
        messages.info(request, "You are already an Affiliate.")
        return redirect("affiliate_dashboard")

    affiliate = None

    if subscriber.subscribed_via.coinpayment_onboarding:
        form = CoinPaymentDetailForm(request.POST)
    else:
        form = StripePaymentDetailForm(request.POST)

    if form.is_valid():
        try:
            with transaction.atomic():
                # Form is valid, create affiliate and update user role
                affiliate = Affiliate.objects.create(
                    subscriber=subscriber,
                    serverowner=subscriber.subscribed_via,
                    discord_id=subscriber.discord_id,
                    server_id=subscriber.subscribed_via.get_choice_server().server_id,
                )

                payment_detail = form.save(commit=False)
                payment_detail.affiliate = affiliate
                payment_detail.save()

                # Update the user's role to be an affiliate
                subscriber.user.is_affiliate = True
                subscriber.user.save()

                messages.success(request, "You have upgraded to being an Affiliate.")
                return redirect("affiliate_dashboard")
        except Exception:
            # Handle any exceptions that might occur during the transaction
            messages.error(request, "An error occurred while upgrading to an affiliate.")
    else:
        # Form is invalid, display error message
        messages.error(request, "An error occurred while submitting your form. Please try again.")

    return redirect("subscriber_dashboard")


##################################################
#                   AFFILIATES                   #
##################################################


@login_required
def affiliate_dashboard(request):
    """Display the affiliate dashboard and allow the affiliate to update payment details."""
    try:
        affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)

        # Get the affiliate's payment detail instance
        payment_detail = affiliate.paymentdetail
        FormClass = CoinPaymentDetailForm if affiliate.serverowner.coinpayment_onboarding else StripePaymentDetailForm

        if request.method == "POST":
            form = FormClass(request.POST, instance=payment_detail)
            if form.is_valid():
                form.save()
                messages.success(request, "Your payment detail has been updated.")
                return redirect("affiliate_dashboard")
            else:
                messages.error(request, "An error occurred while updating your payment details.")
        else:
            form = FormClass(instance=payment_detail)

        template = "affiliate/dashboard.html"
        context = {
            "affiliate": affiliate,
            "form": form,
        }

        return render(request, template, context)
    except ObjectDoesNotExist:
        messages.error(request, "You have trespassed into forbidden territory.")
        return redirect("index")


@login_required
def affiliate_payments(request):
    """Display a paginated list of payments received by the affiliate."""
    try:
        affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)
        payments = affiliate.get_affiliate_payments()
        payments = mk_paginator(request, payments, PAGINATION_ITEMS)

        template = "affiliate/payments.html"
        context = {
            "affiliate": affiliate,
            "payments": payments,
        }

        return render(request, template, context)
    except ObjectDoesNotExist:
        messages.error(request, "You have trespassed into forbidden territory.")
        return redirect("index")


@login_required
def affiliate_invitees(request):
    """Display a paginated list of invitees associated with affiliate."""
    try:
        affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)
        invitations = affiliate.get_affiliate_invitees()
        invitations = mk_paginator(request, invitations, PAGINATION_ITEMS)

        template = "affiliate/invitees.html"
        context = {
            "affiliate": affiliate,
            "invitations": invitations,
        }

        return render(request, template, context)
    except ObjectDoesNotExist:
        messages.error(request, "You have trespassed into forbidden territory.")
        return redirect("index")


##################################################
#                   ERROR PAGES                  #
##################################################


def error_400(request, exception):
    return render(request, "400.html", status=400)


def error_403(request, exception):
    return render(request, "403.html", status=403)


def error_405(request, exception):
    return render(request, "405.html", status=405)


def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
