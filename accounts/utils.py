def select_server(request):
    if not request.user.is_authenticated:
        # User is not authenticated, redirect to login or home page
        return redirect('landing_page')  # Replace 'login' with your desired login URL or home page URL

    if request.method == 'POST':
        form = SubdomainForm(request.POST)
        if form.is_valid():
            subdomain = form.cleaned_data['subdomain']
            server_id = form.cleaned_data['server']
            server_name = get_server_name_by_id(server_id)  # Replace with your own logic to get server name
            # Save the selected server and subdomain to the database
            discord_server = DiscordServer.objects.create(user=request.user, server_name=server_name, subdomain=subdomain)
            # Redirect to the dashboard page
            return redirect('dashboard')  # Replace 'dashboard' with your desired dashboard URL
    else:
        form = SubdomainForm()
    
    # Retrieve the list of servers owned by the authenticated user
    # server_list = get_server_list(request.user)  # Replace with your own logic to retrieve server list
    # Retrieve the server list from the session
    server_list = request.session.get('server_list', [])
    
    context = {
        'form': form,
        'server_list': server_list
    }
    return render(request, 'select_server.html', context)
