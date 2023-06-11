from django import forms
from .models import Profile, StripePlan, Server

class ChooseServerSubdomainForm(forms.Form):
    subdomain = forms.CharField(max_length=20)
    server = forms.ModelChoiceField(queryset=Server.objects.none())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ChooseServerSubdomainForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['server'].queryset = Server.objects.filter(owner__user=user)
            # Add a default choice to the queryset
            self.fields['server'].empty_label = 'Choose a server'

    def save(self, user):
        subdomain = self.cleaned_data['subdomain']
        server = self.cleaned_data['server']
        profile = Profile.objects.get(user=user)
        profile.subdomain = subdomain
        profile.save()
        server.choice_server = True
        server.save()


class PlanForm(forms.Form):
    name = forms.CharField(label='Plan Name', max_length=100)
    amount = forms.IntegerField(label='Amount')
   

# class PlanForm(forms.ModelForm):
#     class Meta:
#         model = StripePlan
#         fields = ['']