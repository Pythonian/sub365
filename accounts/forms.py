from django import forms
from .models import Profile, StripePlan


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['subdomain']


class PlanForm(forms.Form):
    name = forms.CharField(label='Plan Name', max_length=100)
    amount = forms.IntegerField(label='Amount')
   

# class PlanForm(forms.ModelForm):
#     class Meta:
#         model = StripePlan
#         fields = ['']