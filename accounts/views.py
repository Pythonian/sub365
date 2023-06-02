from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.discord.views import DiscordOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render
import requests
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from .models import Profile
from django.contrib.auth.decorators import login_required


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
        
        # Retrieve or create a user account based on the user_info
        # try:
        #     # If the user already exists, update the user information
        #     social_account = SocialAccount.objects.get(provider='discord', uid=user_info.uid)
        #     print(f'Social account user: {social_account.email}')
        #     user = social_account.user
        #     print(f'Second social user: {user.email}')
        # except SocialAccount.DoesNotExist:
        #     # If the user does not exist, create a new user account
        #     user = User(username=user_info.username)
        #     print(f'New user {user.email}')
        
        # # Update or set the user's attributes with the retrieved information
        # user.email = user_info.email
        # user.discord_id = user_info.uid
        # user.avatar = user_info.extra_data.get('avatar', '')
        # user.save()
        # print(f'Django user: {user.email}')

        # # Save the information to the Profile model
        # profile, _ = Profile.objects.get_or_create(user=user)
        # profile.discord_id = user_info.uid
        # profile.username = user_info.username
        # profile.avatar = user_info.extra_data.get('avatar', '')
        # profile.save()
        # print(f'Profile user: {profile.email}')

        # Retrieve user information from the social account
        social_account = SocialAccount.objects.get(provider='discord', user=request.user)
        user_info = social_account.extra_data

        # Update the profile with the retrieved information
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            # Create a new profile if it doesn't exist
            profile = Profile.objects.create(user=request.user)

        profile.discord_id = user_info.get('id', '')
        profile.username = user_info.get('username', '')
        profile.avatar = user_info.get('avatar', '')
        profile.save()
        
        # Save the access token to the social account
        social_token = SocialToken(app=app, token=access_token)
        social_token.account = social_account
        social_token.token_secret = ''
        social_token.save()

        # Retrieve the access token from the callback URL parameters
        access_token = request.GET.get('access_token')
        
        # Make a request to the Discord API to get the user's server information
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        response = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers)

        if response.status_code == 200:
            server_list = response.json()
            
            # Store the server list in the session
            request.session['server_list'] = server_list
            
            # Redirect to the select_server view with the server list
            return redirect('dashboard')
        else:
            # Handle API error
            messages.error(request, "Failed to retrieve server information from Discord.")
            return redirect('landing_page')  
            
    # Handle the case when authentication fails
    return redirect('landing_page')


def dashboard(request):
    profile = SocialAccount.objects.get(provider='discord', user=request.user)
    print(profile)

    context = {
        'profile': profile
    }
    return render(request, 'dashboard.html', context)