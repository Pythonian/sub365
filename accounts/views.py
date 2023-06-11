from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.contrib.auth import login
from django.contrib import messages
from allauth.socialaccount.providers.discord.views import DiscordOAuth2Adapter
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse
import requests
import stripe
from django.conf import settings
from django.contrib.auth import login, get_backends

from .models import Profile, StripePlan, User, Server
from .forms import PlanForm, ChooseServerSubdomainForm

stripe.api_key = settings.STRIPE_SECRET_KEY


def landing_page(request):
    template = 'landing.html'
    context = {}
    return render(request, template, context)


def discord_callback(request):
    # Retrieve the authorization code from the URL parameters
    code = request.GET.get('code')
    if code:
        # Prepare the payload for the token request
        payload = {
            'client_id': settings.DISCORD_CLIENT_ID,
            'client_secret': settings.DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'http://127.0.0.1:8000/accounts/discord/login/callback/',
            'scope': 'identify guilds',
        }

        # Make the POST request to obtain the access token
        token_url = 'https://discord.com/api/oauth2/token'
        response = requests.post(token_url, data=payload)

        # Check the status code
        if response.status_code == 200:
            # Access token obtained successfully
            access_token = response.json().get('access_token')

            # Use the access token to retrieve user information or perform other actions
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
            }

            response = requests.get('https://discord.com/api/users/@me', headers=headers)
            if response.status_code == 200:
                # Get the user information from the response
                user_info = response.json()

            guild_response = requests.get('https://discord.com/api/users/@me/guilds', headers=headers)
            if guild_response.status_code == 200:
                # Gets all the discord servers joined by the user
                server_list = guild_response.json()
                # Process the server list to only returned servers owned by user
                owned_servers = []
                if server_list:
                    for server in server_list:
                        server_id = server['id']
                        server_name = server['name']
                        permissions = server['permissions']

                        # Check if user owns the server (ADMINISTRATOR permission)
                        if permissions & 0x00000008 == 0x00000008:
                            owned_servers.append({
                                'id': server_id,
                                'name': server_name
                            })

                # Retrieve or create the user based on Discord information
                try:
                    social_account = SocialAccount.objects.get(provider='discord', uid=user_info['id'])
                    user = social_account.user
                except (SocialAccount.DoesNotExist, IndexError):
                    # Create a new user and social account
                    user = User.objects.create_user(username=user_info['username'])
                    social_account = SocialAccount.objects.create(
                        user=user, provider='discord', uid=user_info['id'], extra_data=user_info)
                    profile = Profile.objects.get(user=user)
                    profile.discord_id = user_info.get('id', '')
                    profile.username = user_info.get('username', '')
                    profile.avatar = user_info.get('avatar', '')
                    profile.email = user_info.get('email', '')
                    profile.save()
                    
                    for server in owned_servers:
                        profile_server = Server.objects.create(owner=profile)
                        profile_server.server_id = server['id']
                        profile_server.name = server['name']
                        profile_server.save()
                    
                # Set the backend attribute on the user
                user.backend = f"{get_backends()[0].__module__}.{get_backends()[0].__class__.__name__}"
                login(request, user, backend=user.backend)
                
                return redirect('choose_name')
            else:
                print("Failed to retrieve user's server list.")
                return HttpResponse('Failed to retrieve user\'s server list.')
        else:
            print("Failed to obtain access token.")
            return HttpResponse('Failed to obtain access token.')

    return redirect('landing_page')


@login_required
def choose_name(request):
    if request.user.profile.subdomain:
        return redirect('dashboard')
    if request.method == 'POST':
        form = ChooseServerSubdomainForm(request.POST, user=request.user)
        if form.is_valid():
            subdomain = form.cleaned_data['subdomain']
            server = form.cleaned_data['server']
            # Update the server choice_server flag
            server.choice_server = True
            server.save()
            return redirect('create_stripe_account')
        else:
            messages.warning(request, "An Error occured")
    else:
        form = ChooseServerSubdomainForm(user=request.user)

    context = {
        'form': form,
        'server_list': request.user.profile.servers.all(),
    }

    return render(request, 'choose_name.html', context)


def create_stripe_account(request):
    # Create a Stripe account for the user
    connected_account = stripe.Account.create(
        type='standard',
     )
    
    # Retrieve the Stripe account ID
    stripe_account_id = connected_account.id
    
    # Update the Stripe account ID for the current user
    profile = request.user.profile
    profile.stripe_account_id = stripe_account_id
    profile.save()
    
    return redirect('collect_user_info')


def collect_user_info(request):
    profile = request.user.profile
    stripe_account_id = profile.stripe_account_id

    # Generate an account link for the onboarding process    
    account_link = stripe.AccountLink.create(
        account=stripe_account_id,
        refresh_url=request.build_absolute_uri(reverse('stripe_refresh')),
        return_url=request.build_absolute_uri(reverse('dashboard')),
        type='account_onboarding',
    )
    
    # Redirect the user to the Stripe onboarding flow
    return redirect(account_link.url)


@login_required
def dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)

    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            plan_name = form.cleaned_data['name']
            plan_amount = form.cleaned_data['amount']
            plan_currency = 'usd'
            plan_interval = 'month'
            
            try:
                # Create the plan on Stripe
                stripe_plan = stripe.Plan.create(
                    product={
                        'name': plan_name,
                    },
                    amount=plan_amount,
                    currency=plan_currency,
                    interval=plan_interval,
                )
                
                # Save the plan details to the database
                stripe_plan_obj = StripePlan.objects.create(
                    user=request.user,
                    plan_id=stripe_plan.id,
                    name=plan_name,
                    amount=plan_amount,
                    currency=plan_currency,
                    interval=plan_interval,
                )
                
                # Redirect the user back to the dashboard with a success message
                messages.success(request, 'Plan successfully created.')
                return redirect('dashboard')
            except stripe.error.StripeError as e:
                # Handle any errors that occur during plan creation
                form.add_error(None, str(e))
    else:
        form = PlanForm()

    # Retrieve the user's Stripe plans from the database
    stripe_plans = StripePlan.objects.filter(user=request.user)
    # Retrieve the user's Stripe account ID from the profile
    profile = Profile.objects.get(user=request.user)
    stripe_account_id = profile.stripe_account_id
    # Retrieve the Stripe plans from the Stripe API using the account ID
    stripe_plans_api = stripe.Plan.list(limit=100, stripe_account=stripe_account_id)
    # Create a dictionary to map the plan IDs to their respective objects
    stripe_plans_dict = {plan.id: plan for plan in stripe_plans_api.data}
    
    # Iterate over the user's Stripe plans and update their objects with the API data
    for plan in stripe_plans:
        if plan.plan_id in stripe_plans_dict:
            plan_object = stripe_plans_dict[plan.plan_id]
            product_object = stripe.Product.retrieve(plan_object.product)
            plan.name = product_object.name
            plan.amount = plan_object.amount
            plan.currency = plan_object.currency
            plan.interval = plan_object.interval
            plan.save()

    # Get the count of plans created by the user
    plan_count = stripe_plans.count()

    # Get the count of subscribers for all plans created by the user
    # subscriber_count = Subscriber.objects.filter(plan__user=request.user).count()

    context = {
        'profile': profile,
        'form': form,
        'stripe_plans': stripe_plans,
        'plan_count': plan_count,
        # 'subscriber_count': subscriber_count
    }
    return render(request, 'dashboard.html', context)


@login_required
def stripe_refresh(request):
    # Get the logged-in user's profile
    profile = Profile.objects.get(user=request.user)

    # Retrieve the Stripe account ID from the request or the Stripe API response
    stripe_account_id = request.GET.get('account_id')

    # Update the profile's stripe_account_id field
    profile.stripe_account_id = stripe_account_id
    profile.save()

    # Redirect the user to the onboarding process
    return redirect('collect_user_info')


@login_required
def create_plan(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            plan_name = form.cleaned_data['name']
            plan_amount = form.cleaned_data['amount']
            plan_currency = 'usd'
            plan_interval = 'month'
            
            try:
                # Create the plan on Stripe
                stripe_plan = stripe.Plan.create(
                    product={
                        'name': plan_name,
                    },
                    amount=plan_amount,
                    currency=plan_currency,
                    interval=plan_interval,
                )
                
                # Save the plan details to the database
                stripe_plan_obj = StripePlan.objects.create(
                    user=request.user,
                    plan_id=stripe_plan.id,
                    name=plan_name,
                    amount=plan_amount,
                    currency=plan_currency,
                    interval=plan_interval,
                )
                
                # Redirect the user back to the dashboard with a success message
                messages.success(request, 'Plan successfully created.')
                return redirect('dashboard')
            except stripe.error.StripeError as e:
                # Handle any errors that occur during plan creation
                form.add_error(None, str(e))
    else:
        form = PlanForm()
    
    return render(request, 'dashboard.html', {'form': form})


@login_required
def delete_plan(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(StripePlan, id=plan_id, user=request.user)
        plan.delete()
    return redirect('dashboard')


@login_required
def list_plans(request, subdomain):
    user_profile = Profile.objects.get(subdomain=subdomain)
    # stripe_plans = user_profile.plans.all()
    user = request.user
    stripe_plans = StripePlan.objects.filter(user=user)
    return render(request, 'plans.html', {'stripe_plans': stripe_plans, 'user_profile': user_profile})


@login_required
def subscribe_to_plan(request, plan_id):
    plan = get_object_or_404(StripePlan, id=plan_id)
    
    # Create a Stripe Checkout Session
    session = stripe.checkout.Session.create(
        success_url=request.build_absolute_uri(reverse('subscribe_success')),
        cancel_url=request.build_absolute_uri(reverse('subscribe_cancel')),
        # payment_method_types=['card'],
        line_items=[
            {
                'price': plan.plan_id,
                'quantity': 1,
            }
        ],
        mode='subscription',
    )
    
    # Redirect the user to the Stripe Checkout page
    return redirect(session.url)


def subscribe_success(request):
    # Handle the successful subscription confirmation
    # You can perform any necessary actions here
    
    return render(request, 'dashboard.html')

def subscribe_cancel(request):
    # Handle the subscription cancellation or failure
    # You can perform any necessary actions here
    
    return render(request, 'dashboard.html')