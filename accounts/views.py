from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_backends, login
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

import requests
import stripe
from allauth.socialaccount.models import SocialAccount

from .forms import ChooseServerSubdomainForm, PlanForm
from .models import Server, ServerOwner, StripePlan, Subscriber, Subscription, User
from .utils import mk_paginator

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    template = "index.html"
    context = {}
    return render(request, template, context)


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
            "scope": "identify guilds",
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
                if state == "subscriber":
                    try:
                        social_account = SocialAccount.objects.get(provider="discord", uid=user_info["id"])
                        user = social_account.user
                        user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                        login(request, user, backend=user.backend)
                        return redirect("dashboard_view")
                    except (SocialAccount.DoesNotExist, IndexError):
                        # Create a new user and social account
                        user = User.objects.create_user(username=user_info["username"], is_subscriber=True)
                        social_account = SocialAccount.objects.create(
                            user=user, provider="discord", uid=user_info["id"], extra_data=user_info
                        )
                        subscriber = Subscriber.objects.get(user=user)
                        subscriber.discord_id = user_info.get("id", "")
                        subscriber.username = user_info.get("username", "")
                        subscriber.avatar = user_info.get("avatar", "")
                        subscriber.email = user_info.get("email", "")
                        subscriber.save()
                        # Associate the subscriber with the ServerOwner based on the subdomain
                        server_owner = ServerOwner.objects.get(subdomain=subdomain)
                        subscriber.subscribed_via = server_owner
                        subscriber.save()
                    user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                    login(request, user, backend=user.backend)
                    return redirect("subscriber_dashboard")
                else:
                    # state is serverowner
                    guild_response = requests.get("https://discord.com/api/users/@me/guilds", headers=headers)
                    if guild_response.status_code == 200:
                        # Gets all the discord servers joined by the user
                        server_list = guild_response.json()
                        # Process the server list to only returned servers owned by user
                        owned_servers = []
                        if server_list:
                            for server in server_list:
                                server_id = server["id"]
                                server_name = server["name"]
                                permissions = server["permissions"]
                                # Check if user owns the server (ADMINISTRATOR permission)
                                if permissions & 0x00000008 == 0x00000008:
                                    owned_servers.append({"id": server_id, "name": server_name})
                    else:
                        return HttpResponse("Failed to retrieve user's server list.")  # TODO Change this

                    try:
                        social_account = SocialAccount.objects.get(provider="discord", uid=user_info["id"])
                        user = social_account.user
                    except (SocialAccount.DoesNotExist, IndexError):
                        # Create a new user and social account
                        user = User.objects.create_user(username=user_info["username"], is_serverowner=True)
                        social_account = SocialAccount.objects.create(
                            user=user, provider="discord", uid=user_info["id"], extra_data=user_info
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
                            owner_server.save()

                    user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                    login(request, user, backend=user.backend)

                    # TODO comment out this code???
                    if request.user.is_serverowner:
                        return redirect("choose_name")
                    else:
                        return redirect("subscriber_dashboard")
        else:
            return HttpResponse("Failed to obtain access token.")  # TODO Change this

    # TODO what happens if code wasnt generated?
    return redirect("index")


def subscribe_redirect(request):
    # Redirect the user to Discord authentication
    subdomain = request.GET.get("subdomain")
    request.session["subdomain_redirect"] = subdomain
    discord_client_id = settings.DISCORD_CLIENT_ID
    redirect_uri = request.build_absolute_uri(reverse("discord_callback"))
    redirect_url = f"https://discord.com/api/oauth2/authorize?client_id={discord_client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify+email&state=subscriber&subdomain={subdomain}"
    return redirect(redirect_url)


@login_required
def choose_name(request):
    if request.user.serverowner.subdomain:
        return redirect("dashboard")
    if request.method == "POST":
        form = ChooseServerSubdomainForm(request.POST, user=request.user)
        if form.is_valid():
            form.save(user=request.user)
            return redirect("create_stripe_account")
        else:
            messages.warning(request, "An error occurred.")
    else:
        form = ChooseServerSubdomainForm(user=request.user)

    context = {
        "form": form,
    }

    return render(request, "choose_name.html", context)


@login_required
def dashboard_view(request):
    if request.user.is_serverowner:
        return redirect("dashboard")
    elif request.user.is_subscriber:
        return redirect("subscriber_dashboard")
    else:
        return redirect("index")


@login_required
def create_stripe_account(request):
    # Create a Stripe account for the user
    connected_account = stripe.Account.create(
        type="standard",
    )

    # Retrieve the Stripe account ID
    stripe_account_id = connected_account.id

    # Update the Stripe account ID for the current user
    serverowner = request.user.serverowner
    serverowner.stripe_account_id = stripe_account_id
    serverowner.save()

    return redirect("collect_user_info")


@login_required
def collect_user_info(request):
    serverowner = request.user.serverowner
    stripe_account_id = serverowner.stripe_account_id

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
    # Get the logged-in user's profile
    profile = ServerOwner.objects.get(user=request.user)

    # Retrieve the Stripe account ID from the request or the Stripe API response
    stripe_account_id = request.GET.get("account_id")

    # Update the profile's stripe_account_id field
    profile.stripe_account_id = stripe_account_id
    profile.save()

    # Redirect the user to the onboarding process
    return redirect("collect_user_info")


@login_required
def dashboard(request):
    profile = get_object_or_404(ServerOwner, user=request.user)

    # Retrieve the user's Stripe plans from the database
    stripe_plans = StripePlan.objects.filter(user=profile).order_by("-subscriber_count")
    # Get the count of plans created by the user
    plan_count = stripe_plans.count()

    # Get the count of subscribers for all plans created by the user
    subscribers = Subscription.objects.filter(subscribed_via=profile)
    subscriber_count = subscribers.count()

    # Calculate the total earnings
    total_earnings = Decimal(0)
    for subscriber in subscribers:
        total_earnings += subscriber.plan.amount

    context = {
        "profile": profile,
        "stripe_plans": stripe_plans[:3],
        "plan_count": plan_count,
        "subscriber_count": subscriber_count,
        "subscribers": subscribers[:3],
        "total_earnings": total_earnings,
    }
    return render(request, "serverowner/dashboard.html", context)


@login_required
def plans(request):
    profile = get_object_or_404(ServerOwner, user=request.user)

    if request.method == "POST":
        form = PlanForm(request.POST)

        if form.is_valid():
            try:
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
                    },
                )

                # Save the product and price details in your database
                stripe_product = form.save(commit=False)
                stripe_product.price_id = price.id
                stripe_product.product_id = product.id
                stripe_product.user = request.user.serverowner
                stripe_product.save()

                messages.success(request, "Plan successfully created.")
                return redirect("plans")
            except stripe.error.StripeError as e:
                form.add_error(None, str(e))
                messages.warning(request, f"{e}")
        else:
            messages.warning(request, "An error occured.")
    else:
        form = PlanForm()

    # Retrieve the user's Stripe plans from the database
    stripe_plans = StripePlan.objects.filter(user=profile)
    # Get the count of plans created by the user
    plan_count = stripe_plans.count()
    stripe_plans = mk_paginator(request, stripe_plans, 9)

    context = {
        "profile": profile,
        "form": form,
        "stripe_plans": stripe_plans,
        "plan_count": plan_count,
    }
    return render(request, "serverowner/plans.html", context)


@login_required
def plan_detail(request, product_id):
    plan = get_object_or_404(StripePlan, id=product_id, user=request.user.serverowner)

    subscribers = Subscription.objects.filter(plan=plan, subscribed_via=request.user.serverowner)
    active_subscribers = subscribers.filter(status=Subscription.SubscriptionStatus.ACTIVE).count()
    subscriber_count = subscribers.count()

    # Calculate the total earnings
    total_earnings = Decimal(0)
    for subscriber in subscribers:
        total_earnings += subscriber.plan.amount

    context = {
        "plan": plan,
        "subscribers": subscribers,
        "subscriber_count": subscriber_count,
        "active_subscribers": active_subscribers,
        "total_earnings": total_earnings,
    }
    return render(request, "serverowner/plan_detail.html", context)


@login_required
def delete_plan(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        plan = get_object_or_404(StripePlan, id=product_id, user=request.user.serverowner)
        # TODO delete Product on stripe
        plan.delete()
        messages.success(request, "Your plan has been successfully deleted.")
    return redirect("plans")


@login_required
def subscribers(request):
    profile = get_object_or_404(ServerOwner, user=request.user)

    # Get the count of subscribers for all plans created by the user
    subscribers = Subscription.objects.filter(subscribed_via=profile)
    subscriber_count = subscribers.count()

    context = {
        "profile": profile,
        "subscriber_count": subscriber_count,
        "subscribers": subscribers,
    }
    return render(request, "serverowner/subscribers.html", context)


@login_required
def subscriber_dashboard(request):
    subscriber = Subscriber.objects.get(user=request.user)
    server_owner = subscriber.subscribed_via
    server = Server.objects.get(owner=server_owner, choice_server=True)

    # Retrieve the plans related to the ServerOwner
    plans = StripePlan.objects.filter(user=server_owner.user.serverowner)

    try:
        subscription = Subscription.objects.filter(subscriber=subscriber, status=Subscription.SubscriptionStatus.ACTIVE).latest()
    except Subscription.DoesNotExist:
        subscription = None

    context = {
        "plans": plans,
        "subscriber": subscriber,
        "server_owner": server_owner,
        "server": server,
        "subscription": subscription,
    }

    return render(request, "subscriber/dashboard.html", context)


@login_required
@require_POST
def subscribe_to_plan(request, product_id):
    plan = get_object_or_404(StripePlan, id=product_id)
    subscriber = Subscriber.objects.get(user=request.user)

    session = stripe.checkout.Session.create(
        success_url=request.build_absolute_uri(reverse("subscription_success")) + f"?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=request.build_absolute_uri(reverse("subscriber_dashboard")),
        line_items=[
            {
                "price": plan.price_id,
                "quantity": 1,
            }
        ],
        mode="subscription",
        customer_email=subscriber.email,
        client_reference_id=subscriber.id, #TODO remove?
    )

    # Calculate the expiration date
    expiration_date = datetime.now() + timedelta(days=30) #TODO get date from stripe

    # Create a new Subscription object
    subscription = Subscription.objects.create(
        subscriber=subscriber,
        subscribed_via=plan.user,
        plan=plan,
        subscription_date=timezone.now(),
        expiration_date=expiration_date,
        subscription_id=session.id,
    )

    # Increment the subscriber count for the plan
    #TODO When a user cancels payment, this still gets incremented
    plan.subscriber_count += 1
    plan.save()

    # Redirect the user to the Stripe Checkout page
    return redirect(session.url)


def subscription_success(request):
    subscriber = Subscriber.objects.get(user=request.user)

    try:
        session_id = request.GET.get('session_id')
        if session_id:
            new_subscription_session = stripe.checkout.Session.retrieve(session_id)
            customer = stripe.Customer.retrieve(new_subscription_session.customer)
            subscriber.stripe_account_id = customer.id
            subscriber.save()
            subscription = get_object_or_404(Subscription, subscriber=subscriber, subscription_id=session_id)
            subscription.status = Subscription.SubscriptionStatus.ACTIVE
            subscription.save()
        else:
            raise Http404()
    except stripe.error.StripeError as e:
        messages.error(request, 'Failed to retrieve subscription information from Stripe.')

    server = Server.objects.get(owner=subscriber.subscribed_via, choice_server=True)
    subscription = get_object_or_404(Subscription, subscriber=subscriber, subscription_id=session_id) #TODO remove

    context = {
        "plans": plans,
        "subscriber": subscriber,
        "server": server,
        "subscription": subscription,
    }

    return render(request, "subscriber/success.html", context)


def error_500(request):
    return render(request, '500.html', status=500)


def error_404(request, exception):
    return render(request, '404.html', status=404)


def error_400(request, exception):
    return render(request, '400.html', status=400)


def error_403(request, exception):
    return render(request, '403.html', status=403)


def error_405(request, exception):
    return render(request, "405.html")
