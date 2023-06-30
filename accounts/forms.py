from django import forms

from .models import ServerOwner, Server, StripePlan


class ChooseServerSubdomainForm(forms.Form):
    """
    Form for choosing a server and subdomain.
    """

    subdomain = forms.CharField(max_length=20)
    server = forms.ModelChoiceField(queryset=Server.objects.none())
    affiliate_commission = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        """
        Initialize the form with the user and populate the server choices with
        servers of the current user.
        """
        user = kwargs.pop('user', None)
        super(ChooseServerSubdomainForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['server'].queryset = Server.objects.filter(owner__user=user)
            self.fields['server'].empty_label = 'Choose a server'

    def clean_subdomain(self):
        """
        Validate that the subdomain is unique.
        """
        subdomain = self.cleaned_data.get('subdomain')
        if ServerOwner.objects.filter(subdomain=subdomain).exists():
            raise forms.ValidationError('This subdomain has already been chosen.')
        return subdomain

    def clean_server(self):
        """
        Validate that the server is not already chosen by another user.
        """
        server = self.cleaned_data.get('server')
        subdomain = self.cleaned_data.get('subdomain')

        if server and server.choice_server:
            selected_server_id = server.id
            if selected_server_id and ServerOwner.objects.filter(server_id=selected_server_id, subdomain=subdomain).exists():
                raise forms.ValidationError('This server has already been chosen by another user.')
        return server

    def save(self, user):
        """
        Save the chosen subdomain and mark the server as chosen.
        """
        subdomain = self.cleaned_data['subdomain']
        server = self.cleaned_data['server']
        affiliate_commission = self.cleaned_data['affiliate_commission']
        profile = ServerOwner.objects.get(user=user)
        profile.subdomain = subdomain
        profile.affiliate_commission = affiliate_commission
        profile.save()
        server.choice_server = True
        server.save()


class PlanForm(forms.ModelForm):
    """
    Form for creating a Stripe plan.
    """

    interval_count = forms.IntegerField(min_value=1, max_value=12)

    class Meta:
        model = StripePlan
        fields = ['name', 'amount', 'interval_count', 'description']
