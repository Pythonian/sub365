"""Context processors for adding template context data."""

from .models import Server


def choice_server(request):
    """Add the chosen server to the context.

    Retrieves the server owned by the authenticated user that has been marked as
    the choice server.

    Returns:
        dict: A dictionary containing the 'choice_server' key with the chosen server
              object or None if no server is found.
    """
    choice_server = None

    if request.user.is_authenticated:
        try:
            choice_server = Server.objects.get(
                owner__user=request.user,
                choice_server=True,
            )
        except Server.DoesNotExist:
            choice_server = None

    return {"choice_server": choice_server}
