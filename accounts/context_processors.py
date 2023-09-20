from .models import Server


def choice_server(request):
    """A context processor that adds the chosen server to the context.

    The chosen server is the server owned by the authenticated user
    that has been marked as the choice server.

    Returns:
        dict: A dictionary containing the 'choice_server' key with the chosen server
        object or None if no server is chosen.
    """
    choice_server = None

    if request.user.is_authenticated:
        try:
            # Attempt to retrieve the chosen server for the authenticated user
            choice_server = Server.objects.get(owner__user=request.user, choice_server=True)
        except Server.DoesNotExist:
            # Handle the case when the chosen server does not exist
            choice_server = None

    return {"choice_server": choice_server}
