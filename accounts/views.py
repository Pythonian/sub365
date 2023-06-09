from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.discord.views import DiscordOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
import requests
import stripe
from django.conf import settings

from .models import Profile, StripePlan
from .forms import PlanForm, ProfileForm

stripe.api_key = settings.STRIPE_SECRET_KEY

def landing_page(request):
    template = 'landing.html'
    context = {}
    return render(request, template, context)


def discord_callback(request):
    adapter = DiscordOAuth2Adapter(request)
    client = OAuth2Client(request, adapter)
    token = adapter.parse_token(request)
    app = SocialApp.objects.get(provider='discord')
    provider = app.get_provider()

    if token:
        # Exchange the authorization code for an access token
        access_token = client.get_access_token(token)
        # Retrieve user information from the access token
        user_info = provider.sociallogin_from_response(request, access_token)
        # Retrieve user information from the social account
        social_account = SocialAccount.objects.get(provider='discord', user=request.user)
        user_info = social_account.extra_data

        # Save the access token to the social account
        social_token = SocialToken(app=app, token=access_token)
        social_token.account = social_account
        social_token.token_secret = ''
        social_token.save()

        # Check if the user is already authenticated and has a profile
        if request.user.is_authenticated and Profile.objects.filter(user=request.user).exists():
            return redirect('dashboard')

        # Retrieve the access token from the callback URL parameters
        access_token = request.GET.get('access_token')

        # Make a request to the Discord API to get the user's server information
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        response = requests.get('https://discord.com/api/users/@me/guilds', headers=headers)

        if response.status_code == 200:
            server_list = response.json()

            # Store the server list in the session
            request.session['server_list'] = server_list
            # DEBUG
            print(f'Servers: {server_list}')
            # Redirect to the select_server view with the server list
            return redirect('choose_name')
        else:
            # Handle API error
            messages.error(request, "Failed to retrieve server information from Discord.")
            return redirect('landing_page')

    # Handle the case when authentication fails (Previous code)
    # return redirect('landing_page')

    else:
        # Handle the authorization error
        messages.error(request, 'Failed to authenticate with Discord.')
        return redirect('landing_page')


@login_required
def choose_name(request):
    if request.user.profile.subdomain:
        return redirect('dashboard')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            new_user = SocialAccount.objects.get(provider='discord', user=request.user)
            user_info = new_user.extra_data
            profile = Profile.objects.get(user=request.user)
            profile.subdomain = form.cleaned_data.get('subdomain')
            profile.discord_id = user_info.get('id', '')
            profile.username = user_info.get('username', '')
            profile.avatar = user_info.get('avatar', '')
            profile.email = user_info.get('email', '')
            profile.save()
            # Redirect the user to the Stripe account link
            return redirect('create_stripe_account')
        else:
            return HttpResponse('Error')
    else:
        form = ProfileForm()

    # Retrieve the server list from the session
    server_list = request.session.get('server_list', [])

    context = {
        'form': form,
        'server_list': server_list,
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
    
    # Redirect to the next step, such as a form to collect additional user information
    return redirect('collect_user_info')


def collect_user_info(request):
    # Perform actions on behalf of the user using the Stripe account ID
    # Assuming you have stored the Stripe account ID in the user's profile
    profile = request.user.profile
    stripe_account_id = profile.stripe_account_id
    
    # Use the stripe_account_id to perform actions on behalf of the user
    # For example, you can create an account link to guide the user through onboarding
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
    # profile = Profile.objects.get(user=request.user)

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