###########################
#
#  SUBSCRIBERS
#
###########################


def subscriber_plans(request, subdomain):
    if not request.user.is_authenticated:
        return redirect('subscriber_auth', subdomain=subdomain)
    # Retrieve the UserProfile based on the subdomain
    user_profile = Profile.objects.get(subdomain=subdomain)
    plans = user_profile.plans.all()
    return render(request, 'subscriber_plans.html', {'plans': plans})


@login_required
def subscriber_auth(request, subdomain):
    # Check if the user has already authenticated with Discord
    if SocialAccount.objects.filter(provider='discord', user=request.user).exists():
        return redirect('subscriber_plans', subdomain=subdomain)
    
    adapter = DiscordOAuth2Adapter(request)
    client = OAuth2Client(request, adapter)
    app = SocialApp.objects.get(provider='discord')
    provider = app.get_provider()

    # Redirect the subscriber to Discord for authentication
    redirect_url = request.build_absolute_uri(reverse('subscriber_callback', args=[subdomain]))
    return provider.oauth2_login(request, app, redirect_url)


def subscriber_callback(request, subdomain):
    # Handle the OAuth2 callback from Discord
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

        # Create or update the Subscriber model for the authenticated user
        subscriber, created = Subscriber.objects.get_or_create(user=request.user)
        subscriber.discord_id = user_info.get('id', '')
        subscriber.save()

        return redirect('subscriber_plans', subdomain=subdomain)

    # Redirect to the authentication view if the OAuth2 callback fails
    return redirect('subscriber_auth', subdomain=subdomain)


@login_required
def subscriber_payment(request, subdomain, plan_id):
    profile = Profile.objects.get(user=request.user)
    plan = get_object_or_404(StripePlan, id=plan_id, user=request.user)
    # Create a customer in Stripe
    customer = stripe.Customer.create(
        email=request.user.email,
        source=request.POST['stripeToken']
    )
    
    # Subscribe the customer to the plan
    stripe.Subscription.create(
        customer=customer.id,
        items=[{
            'plan': plan.plan_id,
        }]
    )

    # Save the Stripe customer ID to the profile
    profile.stripe_account_id = customer.id
    profile.save()

    messages.success(request, 'Subscribed successfully!')

    return redirect('subscriber_success')


@login_required
def subscriber_success(request):
    return render(request, 'subscriber_success.html')


            # user_info_url = 'https://discord.com/api/users/@me'
            # user_response = requests.get(user_info_url, headers=headers)
            # if user_response.status_code == 200:
            #     user_info = user_response.json()
            #     # Process user information as needed
            #     print("User Info:", user_info)

            #     # Log in the user
            #     # user = request.user
            #     # login(request, user)
            #     # return redirect('choose_name')
            # else:
            #     print("Failed to retrieve user information.")
            #     return HttpResponse('Failed to retrieve user information.')


# def discord_callback(request):
#     adapter = DiscordOAuth2Adapter(request)
#     client = OAuth2Client(request, adapter)
#     token = adapter.parse_token(request)
#     app = SocialApp.objects.get(provider='discord')
#     provider = app.get_provider()

#     if token:
#         print(token)
#         print("discord callback")
#         request.session['discord'] = 'discord callback'
#         # Exchange the authorization code for an access token
#         access_token = client.get_access_token(token)
#         # Retrieve user information from the access token
#         user_info = provider.sociallogin_from_response(request, access_token)
#         # Retrieve user information from the social account
#         social_account = SocialAccount.objects.get(provider='discord', user=request.user)
#         user_info = social_account.extra_data

#         # Save the access token to the social account
#         social_token = SocialToken(app=app, token=access_token)
#         social_token.account = social_account
#         social_token.token_secret = ''
#         social_token.save()

#         # Check if the user is already authenticated and has a profile
#         if request.user.is_authenticated and Profile.objects.filter(user=request.user).exists():
#             return redirect('dashboard')

#         # Retrieve the access token from the callback URL parameters
#         access_token = request.GET.get('access_token')

#         # Make a request to the Discord API to get the user's server information
#         headers = {
#             # 'Content-Type': 'application/json',
#             'Authorization': f'Bearer {access_token}',
#         }
#         response = requests.get('https://discord.com/api/users/@me/guilds', headers=headers)
#         print(f"discord callback {response}")

#         if response.status_code == 200:
#             server_list = response.json()

#             # Process the server list
#             owned_servers = []
#             if server_list:
#                 for server in server_list:
#                     server_id = server['id']
#                     server_name = server['name']
#                     permissions = server['permissions']

#                     # Check if user owns the server (ADMINISTRATOR permission)
#                     if permissions & 0x00000008 == 0x00000008:
#                         owned_servers.append({
#                             'id': server_id,
#                             'name': server_name
#                         })

#             # Store the server list in the session
#             request.session['server_list'] = owned_servers
#             print(f"Server List: {owned_servers}")

#             return redirect('choose_name')
#         else:
#             print('API Error')
#             # Handle API error
#             messages.error(request, "Failed to retrieve server information from Discord.")
#             return redirect('landing_page')

#     else:
#         # Handle the authorization error
#         print('Auth Error')
#         messages.error(request, 'Failed to authenticate with Discord.')
#         return redirect('landing_page')
