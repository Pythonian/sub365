import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_backends, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

import requests
import stripe
from allauth.account.views import LogoutView
from allauth.socialaccount.models import SocialAccount
from requests.exceptions import RequestException

from .decorators import onboarding_completed, redirect_if_no_subdomain
from .forms import (
    CoinbaseOnboardingForm,
    CoinPaymentDetailForm,
    CoinPlanForm,
    OnboardingForm,
    PaymentDetailForm,
    PlanForm,
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
    Subscriber,
    Subscription,
    User,
)
from .tasks import check_coin_transaction_status, check_coin_withdrawal_status
from .utils import create_hmac_signature, mk_paginator

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_API_KEY


def index(request):
    return render(request, "index.html")


def discord_callback(request):
    # Retrieve values from the URL parameters
    code = request.GET.get("code")
    state = request.GET.get("state")
    subdomain = request.session.get("subdomain_redirect")

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

            response = requests.get(
                "https://discord.com/api/users/@me", headers=headers
            )
            if response.status_code == 200:
                # Get the user information from the response
                user_info = response.json()
                if state == "subscriber":
                    try:
                        social_account = SocialAccount.objects.get(
                            provider="discord", uid=user_info["id"]
                        )
                        user = social_account.user
                        user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                        login(request, user, backend=user.backend)
                        return redirect("dashboard_view")
                    except (SocialAccount.DoesNotExist, IndexError):
                        # Create a new user and social account
                        user = User.objects.create_user(
                            username=user_info["username"], is_subscriber=True
                        )
                        social_account = SocialAccount.objects.create(
                            user=user,
                            provider="discord",
                            uid=user_info["id"],
                            extra_data=user_info,
                        )
                        subscriber = Subscriber.objects.get(user=user)
                        subscriber.discord_id = user_info.get("id", "")
                        subscriber.username = user_info.get("username", "")
                        subscriber.avatar = user_info.get("avatar", "")
                        subscriber.email = user_info.get("email", "")
                        subscriber.save()
                        server_owner = ServerOwner.objects.get(subdomain=subdomain)
                        subscriber.subscribed_via = server_owner
                        subscriber.save()
                    user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                    login(request, user, backend=user.backend)
                    return redirect("dashboard_view")
                else:
                    # state is serverowner
                    guild_response = requests.get(
                        "https://discord.com/api/users/@me/guilds", headers=headers
                    )
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
                                server_owner = server["owner"]
                                # Check if user owns the server
                                if server_owner:
                                    owned_servers.append(
                                        {
                                            "id": server_id,
                                            "name": server_name,
                                            "icon": server_icon,
                                        }
                                    )
                    else:
                        # Redirect user and show a message to create a server
                        messages.info(
                            request,
                            "You do not have any servers. Please create a server on Discord before continuing.",
                        )
                        return redirect("index")

                    try:
                        social_account = SocialAccount.objects.get(
                            provider="discord", uid=user_info["id"]
                        )
                        user = social_account.user
                    except (SocialAccount.DoesNotExist, IndexError):
                        # Create a new user and social account
                        user = User.objects.create_user(
                            username=user_info["username"], is_serverowner=True
                        )
                        social_account = SocialAccount.objects.create(
                            user=user,
                            provider="discord",
                            uid=user_info["id"],
                            extra_data=user_info,
                        )
                        serverowner = ServerOwner.objects.get(user=user)
                        serverowner.discord_id = user_info.get("id", "")
                        serverowner.username = user_info.get("username", "")
                        serverowner.avatar = user_info.get("avatar", "")
                        serverowner.email = user_info.get("email", "")
                        serverowner.save()

                        for server in owned_servers:
                            owner_server = Server.objects.create(owner=serverowner)
                            owner_server.server_id = server["id"]
                            owner_server.name = server["name"]
                            owner_server.icon = server["icon"]
                            owner_server.save()

                    user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                    login(request, user, backend=user.backend)

                    return redirect("dashboard_view")
        else:
            messages.error(request, "Failed to obtain access token.")
            return redirect("index")

    messages.error(request, "Your discord authorization was aborted.")
    return redirect("index")


def subscribe_redirect(request):
    """Redirect the user to Discord authentication."""
    if request.user.is_authenticated:
        return redirect("dashboard_view")
    subdomain = request.GET.get("ref")
    request.session["subdomain_redirect"] = subdomain
    discord_client_id = settings.DISCORD_CLIENT_ID
    redirect_uri = request.build_absolute_uri(reverse("discord_callback"))
    redirect_url = f"https://discord.com/api/oauth2/authorize?client_id={discord_client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify+email&state=subscriber&subdomain={subdomain}"  # noqa
    return redirect(redirect_url)


@login_required
def onboarding(request):
    """Handle the onboarding of a Serverowner."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    if serverowner.stripe_account_id or serverowner.coinbase_onboarding:
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
                return redirect("onboarding_crypto")
    else:
        form = OnboardingForm(user=request.user)

    template = "onboarding.html"
    context = {
        "form": form,
    }

    return render(request, template, context)


@login_required
def onboarding_crypto(request):
    """Handle the onboarding process for connecting with coinbase payments."""
    try:
        serverowner = request.user.serverowner
        if serverowner.coinbase_onboarding:
            return redirect("dashboard")
    except ObjectDoesNotExist:
        messages.error(request, "You have trespassed into forbidden territory.")
        return redirect("index")

    if request.method == "POST":
        form = CoinbaseOnboardingForm(request.POST)
        if form.is_valid():
            # Get the API keys entered by the user
            api_secret_key = form.cleaned_data["coinbase_api_secret_key"]
            api_public_key = form.cleaned_data["coinbase_api_public_key"]
            try:
                # Make the API request to verify the coinbase API keys
                endpoint = "https://www.coinpayments.net/api.php"
                data = f"version=1&cmd=get_basic_info&key={api_public_key}&format=json"
                header = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "HMAC": create_hmac_signature(data, api_secret_key),
                }
                response = requests.post(endpoint, data=data, headers=header)
                response.raise_for_status()
                result = response.json()["result"]
                if result:
                    serverowner = request.user.serverowner
                    serverowner.coinbase_api_secret_key = api_secret_key
                    serverowner.coinbase_api_public_key = api_public_key
                    serverowner.coinbase_onboarding = True
                    serverowner.save()
                    return redirect("dashboard_view")
                else:
                    form.add_error(None, "Invalid Coinbase API keys.")
            except RequestException as e:
                # RequestException includes issues like network errors, invalid responses etc.
                logger.error(f"Failed to verify Coinbase API keys: {e}")
                form.add_error(None, f"Failed to verify Coinbase API keys: {e}")
            except ValueError as e:
                # Raised if there is an issue with parsing JSON response
                logger.error(f"Failed to verify Coinbase API keys: {e}")
                form.add_error(None, f"Failed to parse API response: {e}")
            except Exception as e:
                # Catch any other unexpected exceptions and log them
                logger.exception(f"An unexpected error occurred: {e}")
                form.add_error(
                    None, "An unexpected error occurred. Please try again later."
                )
    else:
        form = CoinbaseOnboardingForm()

    template = "onboarding_crypto.html"
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
        return redirect("index")


def create_webhook_endpoint(request, stripe_account_id):
    webhook_endpoint = stripe.WebhookEndpoint.create(
        # url=request.build_absolute_uri(reverse("stripe_webhook")),
        url="http://web:8000/webhook/",
        enabled_events=[
            "invoice.payment_succeeded", "invoice.paid",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
        ],
        connect=True,
    )
    return webhook_endpoint


@login_required
def create_stripe_account(request):
    """Create a Stripe account for the user."""
    connected_account = stripe.Account.create(
        type="standard",
    )

    # Retrieve the Stripe account ID
    stripe_account_id = connected_account.id

    try:
        # Update the Stripe account ID for the current user
        serverowner = request.user.serverowner
        serverowner.stripe_account_id = stripe_account_id
        serverowner.save()
        # Create a webhook endpoint for the newly created connected account
        # create_webhook_endpoint(request, stripe_account_id)
    except ObjectDoesNotExist:
        messages.error(request, "You have tresspassed to forbidden territory.")
        return redirect("index")

    return redirect("collect_user_info")


@login_required
def collect_user_info(request):
    """Collect additional user info for Stripe onboarding."""
    try:
        serverowner = request.user.serverowner
        stripe_account_id = serverowner.stripe_account_id
    except ObjectDoesNotExist:
        messages.error(request, "You have tresspassed to forbidden territory.")
        return redirect("index")

    # Generate an account link for the onboarding process
    account_link = stripe.AccountLink.create(
        account=stripe_account_id,
        refresh_url=request.build_absolute_uri(reverse("stripe_refresh")),
        return_url=request.build_absolute_uri(reverse("dashboard")),
        type="account_onboarding",
    )

    # Redirect the user to the Stripe onboarding flow
    return redirect(account_link.url)


@login_required
def stripe_refresh(request):
    """Handle refreshing the Stripe account information."""
    try:
        serverowner = request.user.serverowner

        # Retrieve the Stripe account ID from the request or the Stripe API response
        stripe_account_id = request.GET.get("account_id")

        # Update the profile's stripe_account_id field
        serverowner.stripe_account_id = stripe_account_id
        serverowner.save()
    except ObjectDoesNotExist:
        messages.error(request, "You have tresspassed to forbidden territory.")
        return redirect("index")

    # Redirect the user to the onboarding process
    return redirect("collect_user_info")


@login_required
@require_POST
def delete_account(request):
    request.user.delete()
    messages.success(request, "Your account has been deleted.")
    return LogoutView.as_view()(request)


##################################################
#                   SERVER OWNER                 #
##################################################


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def dashboard(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    discord_client_id = settings.DISCORD_CLIENT_ID

    template = "serverowner/dashboard.html"
    context = {
        "serverowner": serverowner,
        "discord_client_id": discord_client_id,
    }

    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def plans(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    if serverowner.coinbase_onboarding:
        if request.method == "POST":
            form = CoinPlanForm(request.POST)
            if form.is_valid():
                coin_plan = form.save(commit=False)
                coin_plan.serverowner = serverowner
                coin_plan.save()
                messages.success(
                    request, "Your Subscription Plan has been successfully created."
                )
                return redirect("plans")
            else:
                messages.error(request, "An error occured while creating your Plan.")
        else:
            form = CoinPlanForm()
        coin_plans = serverowner.get_plans()
        coin_plans = mk_paginator(request, coin_plans, 9)

    else:
        if request.method == "POST":
            form = PlanForm(request.POST)
            if form.is_valid():
                try:
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

                    # Save the product and price details in your database
                    stripe_product = form.save(commit=False)
                    stripe_product.price_id = price.id
                    stripe_product.product_id = product.id
                    stripe_product.user = serverowner
                    stripe_product.save()

                    messages.success(
                        request, "Your Subscription Plan has been successfully created."
                    )
                    return redirect("plans")
                except stripe.error.StripeError as e:
                    logger.exception(
                        "An error occurred during a Stripe API call: %s", str(e)
                    )
                    messages.error(
                        request,
                        "An error occurred while processing your request. Please try again later.",
                    )
            else:
                messages.error(request, "An error occured while creating your Plan.")
        else:
            form = PlanForm()
        # Retrieve the user's Stripe plans from the database and paginate
        stripe_plans = serverowner.get_plans()
        stripe_plans = mk_paginator(request, stripe_plans, 9)

    if serverowner.coinbase_onboarding:
        template = "serverowner/plans/coinbase/list.html"
        context = {
            "serverowner": serverowner,
            "form": form,
            "coin_plans": coin_plans,
        }
    else:
        template = "serverowner/plans/stripe/list.html"
        context = {
            "serverowner": serverowner,
            "form": form,
            "stripe_plans": stripe_plans,
        }
    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
def plan_detail(request, product_id):
    """Display detailed information about a specific plan."""
    if request.user.serverowner.coinbase_onboarding:
        plan = get_object_or_404(
            CoinPlan, id=product_id, serverowner=request.user.serverowner
        )
        subscribers = plan.get_coinplan_subscribers()
        subscribers = mk_paginator(request, subscribers, 12)

        if request.method == "POST":
            form = CoinPlanForm(request.POST, instance=plan)
            if form.is_valid():
                plan = form.save()
                messages.success(
                    request, "Your Subscription Plan has been successfully updated."
                )
                return redirect("plan", product_id=plan.id)
            else:
                messages.error(request, "An error occurred while updating your Plan.")
        else:
            form = CoinPlanForm(instance=plan)

    else:
        plan = get_object_or_404(
            StripePlan, id=product_id, user=request.user.serverowner
        )
        subscribers = plan.get_stripeplan_subscribers()
        subscribers = mk_paginator(request, subscribers, 12)

        if request.method == "POST":
            form = PlanForm(request.POST, instance=plan)

            if form.is_valid():
                try:
                    # Update the product on Stripe
                    product_params = {
                        "name": form.cleaned_data["name"],
                        "description": form.cleaned_data["description"],
                        "active": True,
                    }

                    product = stripe.Product.modify(  # noqa
                        plan.product_id, **product_params
                    )

                    # Save the updated plan details in the database
                    plan = form.save()

                    messages.success(
                        request, "Your Subscription Plan has been successfully updated."
                    )
                    return redirect("plan", product_id=plan.id)
                except stripe.error.StripeError as e:
                    logger.exception(
                        "An error occurred during a Stripe API call: %s", str(e)
                    )
                    messages.error(
                        request,
                        "An error occurred while processing your request. Please try again later.",
                    )
            else:
                messages.error(request, "An error occurred while updating your Plan.")
        else:
            form = PlanForm(instance=plan)

    if request.user.serverowner.coinbase_onboarding:
        template = "serverowner/plans/coinbase/detail.html"
    else:
        template = "serverowner/plans/stripe/detail.html"
    context = {
        "plan": plan,
        "form": form,
        "subscribers": subscribers,
    }

    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
@require_POST
def deactivate_plan(request):
    """Deactivate a plan."""

    if request.user.serverowner.coinbase_onboarding:
        if request.method == "POST":
            product_id = request.POST.get("product_id")
            plan = get_object_or_404(
                CoinPlan, id=product_id, serverowner=request.user.serverowner
            )
            # Update the plan status in the database
            plan.status = CoinPlan.PlanStatus.INACTIVE
            plan.save()
            messages.success(request, "Your plan has been successfully deactivated.")

        return redirect("plan", plan.id)
    else:
        if request.method == "POST":
            product_id = request.POST.get("product_id")
            plan = get_object_or_404(
                StripePlan, id=product_id, user=request.user.serverowner
            )

            try:
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

                messages.success(
                    request, "Your plan has been successfully deactivated."
                )
            except stripe.error.StripeError as e:
                logger.exception(
                    "An error occurred during a Stripe API call: %s", str(e)
                )
                messages.error(
                    request,
                    "An error occurred while processing your request. Please try again later.",
                )
        return redirect("plan", plan.id)


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def subscribers(request):
    """Display the subscribers of a user's plans."""
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    if serverowner.coinbase_onboarding:
        template = "serverowner/subscribers/coinbase/list.html"
    else:
        template = "serverowner/subscribers/stripe/list.html"

    subscribers = serverowner.get_subscribed_users()
    subscribers = mk_paginator(request, subscribers, 12)

    context = {
        "serverowner": serverowner,
        "subscribers": subscribers,
    }
    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
def subscriber_detail(request, id):
    subscriber = get_object_or_404(Subscriber, id=id)
    subscriptions = subscriber.get_subscriptions()
    subscriptions = mk_paginator(request, subscriptions, 12)

    if request.user.serverowner.coinbase_onboarding:
        try:
            # Retrieve the latest active subscription for the subscriber
            subscription = CoinSubscription.objects.filter(
                subscriber=subscriber, status=CoinSubscription.SubscriptionStatus.ACTIVE
            ).latest()
        except CoinSubscription.DoesNotExist:
            subscription = None
    else:
        try:
            # Retrieve the latest active subscription for the subscriber
            subscription = Subscription.objects.filter(
                subscriber=subscriber, status=Subscription.SubscriptionStatus.ACTIVE
            ).latest()
        except Subscription.DoesNotExist:
            subscription = None

    template = "serverowner/subscribers/detail.html"
    context = {
        "subscriber": subscriber,
        "subscription": subscription,
        "subscriptions": subscriptions,
    }

    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def affiliates(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)

    affiliates = Affiliate.objects.filter(serverowner=serverowner)
    affiliates = mk_paginator(request, affiliates, 9)

    template = "serverowner/affiliate/list.html"
    context = {
        "serverowner": serverowner,
        "affiliates": affiliates,
    }

    return render(request, template, context)


@login_required
def affiliate_detail(request, id):
    subscriber = get_object_or_404(Subscriber, id=id)
    affiliate = get_object_or_404(Affiliate, subscriber=subscriber)
    invitations = affiliate.get_affiliate_invitees()
    invitations = mk_paginator(request, invitations, 12)

    template = "serverowner/affiliate/detail.html"
    context = {
        "affiliate": affiliate,
        "invitations": invitations,
    }

    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def pending_affiliate_payment(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    serverowner_id = serverowner.id
    affiliates = serverowner.get_pending_affiliates()
    affiliates = mk_paginator(request, affiliates, 20)

    if serverowner.coinbase_onboarding:
        if request.method == "POST":
            affiliate_id = request.POST.get("affiliate_id")
            if affiliate_id is not None:
                affiliate = Affiliate.objects.filter(pk=affiliate_id).first()
                if affiliate is not None:
                    try:
                        endpoint = "https://www.coinpayments.net/api.php"
                        data = (
                            f"version=1&cmd=create_withdrawal&amount={serverowner.total_pending_btc_commissions}&currency="
                            + settings.COINBASE_CURRENCY
                            + f"&add_tx_fee=1&auto_confirm=1&address={affiliate.paymentdetail.body}&key={serverowner.coinbase_api_public_key}&format=json"
                        )
                        header = {
                            "Content-Type": "application/x-www-form-urlencoded",
                            "HMAC": create_hmac_signature(
                                data, serverowner.coinbase_api_secret_key
                            ),
                        }
                        response = requests.post(endpoint, data=data, headers=header)
                        response.raise_for_status()
                        result = response.json()["result"]
                        if result:
                            # check_coin_withdrawal_status.apply_async()
                            check_coin_withdrawal_status.apply_async(
                                args=(
                                    affiliate_id,
                                    serverowner_id,
                                ),
                            )
                            messages.success(
                                request,
                                "Your coin payment is being sent to the affiliate. A confirmation will be sent soon.",
                            )
                            return redirect("pending_affiliate_payment")
                    except requests.exceptions.RequestException as e:
                        logger.exception(f"Coinbase API request failed: {e}")
                        messages.error(
                            request,
                            "An error occurred while communicating with Coinbase. Please try again later.",
                        )
                        return redirect("pending_affiliate_payment")
                    except (ValueError, KeyError) as e:
                        logger.exception(f"Failed to parse Coinbase API response: {e}")
                        messages.error(
                            request,
                            "An unexpected error occurred while processing the response. Please try again later.",
                        )
                        return redirect("pending_affiliate_payment")
                    except Exception as e:
                        logger.exception(f"An unexpected error occurred: {e}")
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
                    # Update the server owner's total_pending_commissions
                    serverowner.total_pending_commissions = (
                        F("total_pending_commissions") - affiliate.pending_commissions
                    )
                    serverowner.save()

                    # Update the affiliate's pending_commissions and total_commissions_paid fields
                    affiliate.total_commissions_paid = (
                        F("total_commissions_paid") + affiliate.pending_commissions
                    )
                    affiliate.pending_commissions = Decimal(0)
                    affiliate.last_payment_date = timezone.now()
                    affiliate.save()

                    # Mark the associated AffiliatePayment instances as paid
                    affiliate_payments = AffiliatePayment.objects.filter(
                        serverowner=serverowner, affiliate=affiliate, paid=False
                    )
                    affiliate_payments.update(
                        paid=True, date_payment_confirmed=timezone.now()
                    )

                    messages.success(request, "Payment confirmed.")
                    return redirect("pending_affiliate_payment")

    template = "serverowner/affiliate/payment_pending.html"
    context = {
        "serverowner": serverowner,
        "affiliates": affiliates,
    }

    return render(request, template, context)


@login_required
@redirect_if_no_subdomain
@onboarding_completed
def confirmed_affiliate_payment(request):
    serverowner = get_object_or_404(ServerOwner, user=request.user)
    affiliates = serverowner.get_confirmed_affiliate_payments()
    affiliates = mk_paginator(request, affiliates, 12)

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
    # Retrieve the subscriber based on the logged-in user
    subscriber = get_object_or_404(Subscriber, user=request.user)

    # Retrieve the server owner associated with the subscriber
    server_owner = subscriber.subscribed_via

    if server_owner.coinbase_onboarding:
        plans = CoinPlan.objects.filter(
            serverowner=server_owner, status=CoinPlan.PlanStatus.ACTIVE
        )
        plans = mk_paginator(request, plans, 9)
        try:
            # Retrieve the latest active subscription for the subscriber
            latest_subscription = CoinSubscription.objects.filter(
                subscriber=subscriber, status=CoinSubscription.SubscriptionStatus.ACTIVE
            ).latest()
        except CoinSubscription.DoesNotExist:
            latest_subscription = None
        # Retrieve all the subscriptions done by the subscriber
        subscriptions = CoinSubscription.objects.filter(
            subscriber=subscriber).exclude(status=CoinSubscription.SubscriptionStatus.INACTIVE)
        subscriptions = mk_paginator(request, subscriptions, 12)
        form = CoinPaymentDetailForm()
    else:
        # Retrieve the plans related to the ServerOwner
        plans = StripePlan.objects.filter(
            user=server_owner.user.serverowner, status=StripePlan.PlanStatus.ACTIVE
        )
        plans = mk_paginator(request, plans, 9)

        try:
            # Retrieve the latest active subscription for the subscriber
            latest_subscription = Subscription.objects.filter(
                subscriber=subscriber, status=Subscription.SubscriptionStatus.ACTIVE
            ).latest()
        except Subscription.DoesNotExist:
            latest_subscription = None

        # Retrieve all the subscriptions done by the subscriber
        subscriptions = Subscription.objects.filter(
            subscriber=subscriber).exclude(status=Subscription.SubscriptionStatus.INACTIVE)
        subscriptions = mk_paginator(request, subscriptions, 12)
        form = PaymentDetailForm()

    template = "subscriber/dashboard.html"

    context = {
        "plans": plans,
        "subscriber": subscriber,
        "server_owner": server_owner,
        "subscription": latest_subscription,
        "subscriptions": subscriptions,
        "form": form,
    }

    return render(request, template, context)


@login_required
@require_POST
def subscribe_to_coin_plan(request, plan_id):
    plan = get_object_or_404(CoinPlan, id=plan_id)
    subscriber = get_object_or_404(Subscriber, user=request.user)

    try:
        endpoint = "https://www.coinpayments.net/api.php"
        data = (
            f"version=1&cmd=create_transaction&amount={plan.amount}&currency1=USD&currency2="
            + settings.COINBASE_CURRENCY
            + f"&buyer_email={subscriber.email}&key={subscriber.subscribed_via.coinbase_api_public_key}&format=json"
        )
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "HMAC": create_hmac_signature(
                data, subscriber.subscribed_via.coinbase_api_secret_key
            ),
        }
        response = requests.post(endpoint, data=data, headers=header)
        response.raise_for_status()
        result = response.json()["result"]
        if result:
            checkout_url = result["checkout_url"]
            coin_subscription = CoinSubscription.objects.create(
                subscriber=subscriber,
                subscribed_via=subscriber.subscribed_via,
                plan=plan,
                subscription_id=result["txn_id"],
                coin_amount=result["amount"],
                address=result["address"],
                checkout_url=result["checkout_url"],
                status_url=result["status_url"],
                qrcode_url=result["qrcode_url"],
                status=CoinSubscription.SubscriptionStatus.INACTIVE,
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
def subscribe_to_plan(request, product_id):
    plan = get_object_or_404(StripePlan, id=product_id)
    subscriber = get_object_or_404(Subscriber, user=request.user)
    if subscriber.stripe_customer_id:
        try:
            session = stripe.checkout.Session.create(
                success_url=request.build_absolute_uri(reverse("subscription_success"))
                + f"?session_id={{CHECKOUT_SESSION_ID}}&subscribed_plan={plan.id}",
                cancel_url=request.build_absolute_uri(reverse("subscriber_dashboard")),
                payment_method_types=["us_bank_account"],
                line_items=[
                    {
                        "price": plan.price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                customer=subscriber.stripe_customer_id,
            )

        except stripe.error.StripeError as e:
            logger.exception("An error occurred during a Stripe API call: %s", str(e))
            messages.error(
                request,
                "An error occurred while processing your request. Please try again later.",
            )
            return redirect("subscriber_dashboard")
    else:
        try:
            session = stripe.checkout.Session.create(
                success_url=request.build_absolute_uri(reverse("subscription_success"))
                + f"?session_id={{CHECKOUT_SESSION_ID}}&subscribed_plan={plan.id}",
                cancel_url=request.build_absolute_uri(reverse("subscriber_dashboard")),
                payment_method_types=["us_bank_account"],
                line_items=[
                    {
                        "price": plan.price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                customer_email=subscriber.email,
            )

        except stripe.error.StripeError as e:
            logger.exception("An error occurred during a Stripe API call: %s", str(e))
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

        session_id = request.GET.get("session_id")
        plan_id = request.GET.get("subscribed_plan")
        plan = get_object_or_404(StripePlan, id=plan_id)

        if Subscription.objects.filter(session_id=session_id).exists():
            return redirect("subscriber_dashboard")

        session_info = stripe.checkout.Session.retrieve(session_id)

        subscription_id = session_info.subscription
        subscription_info = stripe.Subscription.retrieve(subscription_id)

        current_period_end = subscription_info.current_period_end
        expiration_date = datetime.fromtimestamp(current_period_end)

        subscription = Subscription.objects.create(
            subscriber=subscriber,
            subscribed_via=subscriber.subscribed_via,
            plan=plan,
            subscription_date=timezone.now(),
            expiration_date=expiration_date,
            subscription_id=subscription_id,
            session_id=session_id,
            status=Subscription.SubscriptionStatus.ACTIVE,
        )

        try:
            affiliateinvitee = AffiliateInvitee.objects.get(
                invitee_discord_id=subscriber.discord_id
            )
            affiliatepayment = AffiliatePayment.objects.create(  # noqa
                serverowner=subscriber.subscribed_via,
                affiliate=affiliateinvitee.affiliate,
                subscriber=subscriber,
                amount=affiliateinvitee.get_affiliate_commission_payment(),
            )

            affiliateinvitee.affiliate.update_last_payment_date()
            affiliateinvitee.affiliate.pending_commissions = (
                F("pending_commissions")
                + affiliateinvitee.get_affiliate_commission_payment()
            )
            affiliateinvitee.affiliate.save()

            subscriber.subscribed_via.total_pending_commissions = (
                F("total_pending_commissions")
                + affiliateinvitee.get_affiliate_commission_payment()
            )
            subscriber.subscribed_via.save()

        except ObjectDoesNotExist:
            affiliateinvitee = None

        # Increment the subscriber count for the plan
        plan.subscriber_count = F("subscriber_count") + 1
        plan.save()

        # Save the customer ID to the subscriber
        subscriber.stripe_customer_id = session_info.customer
        subscriber.save()

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
    subscriber = get_object_or_404(Subscriber, user=request.user)

    if subscriber.subscribed_via.coinbase_onboarding:
        try:
            coin_subscription = get_object_or_404(
                CoinSubscription,
                subscriber=subscriber,
                status=CoinSubscription.SubscriptionStatus.ACTIVE,
            )
            coin_subscription.status = CoinSubscription.SubscriptionStatus.CANCELED
            coin_subscription.save()
            messages.success(
                request, f"Your subscription has been canceled successfully. It will not be renewed when it expires on {coin_subscription.expiration_date.strftime('%B %d, %Y')}"
            )
        except Http404:
            # If the subscription is not found, it will raise a 404 error with a message
            messages.error(request, "No active subscription found for cancellation.")
            return redirect("subscriber_dashboard")
        return redirect("subscriber_dashboard")
    else:
        try:
            # Retrieve the active subscription for the subscriber
            subscription = get_object_or_404(
                Subscription,
                subscriber=subscriber,
                status=Subscription.SubscriptionStatus.ACTIVE,
            )

            # Cancel the subscription at the end of the billing period
            subscription_stripe = stripe.Subscription.retrieve(subscription.subscription_id)
            subscription_stripe.cancel_at_period_end = True
            subscription_stripe.save()
            # Update the Subscription object
            subscription.status = Subscription.SubscriptionStatus.CANCELED
            subscription.save()

            messages.success(
                request, f"Your subscription has been canceled successfully. It will not be renewed when it expires on {subscription.expiration_date.strftime('%B %d, %Y')}"
            )
        except stripe.error.StripeError as e:
            logger.exception("An error occurred during a Stripe API call: %s", str(e))
            messages.error(
                request,
                "An error occurred while canceling your subscription. Please try again later.",
            )
            return redirect("subscriber_dashboard")

        except Http404:
            # If the subscription is not found, it will raise a 404 error with a message
            messages.error(request, "No active subscription found for cancellation.")
            return redirect("subscriber_dashboard")

        except Exception as e:
            logger.exception("An unexpected error occurred: %s", str(e))
            messages.error(
                request,
                "An unexpected error occurred while processing your request. Please try again later.",
            )

        return redirect("subscriber_dashboard")


@login_required
@require_POST
def upgrade_to_affiliate(request):
    subscriber = get_object_or_404(Subscriber, user=request.user)

    # Check if the subscriber already has an affiliate object
    if hasattr(subscriber, "affiliate"):
        # Subscriber is already an affiliate, redirect to affiliate dashboard
        messages.info(request, "You are already an Affiliate.")
        return redirect("affiliate_dashboard")

    affiliate = None

    if subscriber.subscribed_via.coinbase_onboarding:
        form = CoinPaymentDetailForm(request.POST)
    else:
        form = PaymentDetailForm(request.POST)

    if form.is_valid():
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
    else:
        # Form is invalid, display error message
        messages.error(
            request,
            "An error occurred while submitting your form. Please cross-check your address.")
        return redirect("subscriber_dashboard")


##################################################
#                   AFFILIATES                   #
##################################################


@login_required
def affiliate_dashboard(request):
    affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)
    payment_detail = affiliate.paymentdetail

    if affiliate.serverowner.coinbase_onboarding:
        if request.method == "POST":
            form = CoinPaymentDetailForm(request.POST, instance=payment_detail)
            if form.is_valid():
                payment_detail = form.save(commit=False)
                payment_detail.save()
                messages.success(request, "Your payment detail has been updated.")
                return redirect("affiliate_dashboard")
            else:
                messages.error(request, "An error occured while submitting your form.")
        else:
            form = CoinPaymentDetailForm(instance=payment_detail)
    else:
        if request.method == "POST":
            form = PaymentDetailForm(request.POST, instance=payment_detail)
            if form.is_valid():
                payment_detail = form.save(commit=False)
                payment_detail.save()
                messages.success(request, "Your payment detail has been updated.")
                return redirect("affiliate_dashboard")
            else:
                messages.error(request, "An error occured while submitting your form.")
        else:
            form = PaymentDetailForm(instance=payment_detail)

    template = "affiliate/dashboard.html"
    context = {
        "affiliate": affiliate,
        "form": form,
    }

    return render(request, template, context)


@login_required
def affiliate_payments(request):
    affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)
    payments = affiliate.get_affiliate_payments()
    payments = mk_paginator(request, payments, 12)

    template = "affiliate/payments.html"
    context = {
        "affiliate": affiliate,
        "payments": payments,
    }

    return render(request, template, context)


@login_required
def affiliate_invitees(request):
    affiliate = get_object_or_404(Affiliate, subscriber=request.user.subscriber)
    invitations = affiliate.get_affiliate_invitees()
    invitations = mk_paginator(request, invitations, 12)

    template = "affiliate/invitees.html"
    context = {
        "affiliate": affiliate,
        "invitations": invitations,
    }

    return render(request, template, context)


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
