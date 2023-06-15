from django import forms

from .models import ServerOwner, Server, StripePlan


class ChooseServerSubdomainForm(forms.Form):
    subdomain = forms.CharField(max_length=20)
    server = forms.ModelChoiceField(queryset=Server.objects.none())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ChooseServerSubdomainForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['server'].queryset = Server.objects.filter(owner__user=user)
            self.fields['server'].empty_label = 'Choose a server'

    def clean_subdomain(self):
        subdomain = self.cleaned_data.get('subdomain')
        if ServerOwner.objects.filter(subdomain=subdomain).exists():
            raise forms.ValidationError('This subdomain has already been chosen.')
        return subdomain

    def clean_server(self):
        server = self.cleaned_data.get('server')
        subdomain = self.cleaned_data.get('subdomain')

        if server and server.choice_server:
            selected_server_id = server.id
            if selected_server_id and ServerOwner.objects.filter(server_id=selected_server_id, subdomain=subdomain).exists():
                raise forms.ValidationError('This server has already been chosen by another user.')
        return server

    def save(self, user):
        subdomain = self.cleaned_data['subdomain']
        server = self.cleaned_data['server']
        profile = ServerOwner.objects.get(user=user)
        profile.subdomain = subdomain
        profile.save()
        server.choice_server = True
        server.save()


class PlanForm(forms.ModelForm):
    class Meta:
        model = StripePlan
        fields = ['name', 'amount', 'description']
