from .models import Server


def choice_server(request):
    if request.user.is_authenticated:
        choice_server = Server.objects.filter(owner__user=request.user, choice_server=True).first()
    else:
        choice_server = ''
    return {'choice_server': choice_server}
