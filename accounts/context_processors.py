from .models import Server


def choice_server(request):
    choice_server = Server.objects.filter(owner__user=request.user, choice_server=True).first()
    return {'choice_server': choice_server}
