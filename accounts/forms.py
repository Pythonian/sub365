import re

from django import forms

from .models import Server, ServerOwner, StripePlan, PaymentDetail

DISALLOWED_SUBDOMAINS = [
    "activate",
    "account",
    "accounts",
    "admin",
    "about",
    "administrator",
    "activity",
    "affiliate",
    "auth",
    "authentication",
    "blogs",
    "blog",
    "billing",
    "create",
    "cookie",
    "contact",
    "config",
    "contribute",
    "disable",
    "delete",
    "download",
    "downloads",
    "delete",
    "edit",
    "explore",
    "email",
    "feedback",
    "follow",
    "feed",
    "intranet",
    "jobs",
    "join",
    "login",
    "logout",
    "media",
    "mail",
    "news",
    "newsletter",
    "help",
    "home",
    "privacy",
    "profile",
    "plan",
    "registration",
    "register",
    "remove",
    "root",
    "reviews",
    "review",
    "signin",
    "signup",
    "signout",
    "settings",
    "setting",
    "static",
    "support",
    "status",
    "search",
    "subscribe",
    "shop",
    "sub365",
    "subscriber",
    "terms",
    "term",
    "update",
    "username",
    "user",
    "users",
]


class Lowercase(forms.CharField):
    """Convert values in a field to lowercase."""

    def to_python(self, value):
        return value.lower()


class OnboardingForm(forms.Form):
    """
    Form for choosing a server and subdomain.
    """

    subdomain = Lowercase(
        label="Subdomain",
        min_length=4,
        max_length=20,
        help_text="A unique name to invite subscribers to your server.",
        widget=forms.TextInput(
            attrs={"placeholder": "Enter a subdomain name", "class": "form-control"}
        ),
    )
    server = forms.ModelChoiceField(
        queryset=Server.objects.none(),
        help_text="Choose from a Discord server you own.",
    )
    affiliate_commission = forms.IntegerField(
        min_value=1,
        max_value=99,
        help_text="Percentage of commission to be given to Affiliates.",
        widget=forms.NumberInput(
            attrs={"placeholder": "Enter affiliate commission", "class": "form-control"}
        ),
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize the form with the user and populate the server choices with
        servers of the current user.
        """
        user = kwargs.pop("user", None)
        super(OnboardingForm, self).__init__(*args, **kwargs)
        if user:
            self.fields["server"].queryset = Server.objects.filter(owner__user=user)
            self.fields["server"].empty_label = "Choose a server"

    def clean_subdomain(self):
        """
        Validate that the subdomain is unique.
        """
        subdomain = self.cleaned_data.get("subdomain")
        if ServerOwner.objects.filter(subdomain=subdomain).exists():
            raise forms.ValidationError("This subdomain has already been chosen.")
        if subdomain in DISALLOWED_SUBDOMAINS:
            raise forms.ValidationError("You are not allowed to use this name.")
        if not re.match(r"^[a-z0-9_]+$", subdomain):
            raise forms.ValidationError(
                "Subdomain can only contain lowercase letters, numbers, and hyphens."
            )
        return subdomain

    def clean_affiliate_commission(self):
        """
        Validate that the commission is between 1 and 99.
        """
        affiliate_commission = self.cleaned_data.get("affiliate_commission")
        if affiliate_commission < 1 or affiliate_commission > 99:
            raise forms.ValidationError(
                "Affiliate commission must be between 1 and 99."
            )
        return affiliate_commission

    def clean_server(self):
        """
        Validate that the server is not already chosen by another user.
        """
        server = self.cleaned_data.get("server")
        subdomain = self.cleaned_data.get("subdomain")

        if server and server.choice_server:
            selected_server_id = server.id
            if (
                selected_server_id
                and ServerOwner.objects.filter(
                    server_id=selected_server_id, subdomain=subdomain
                ).exists()
            ):
                raise forms.ValidationError(
                    "This server has already been chosen by another user."
                )
        return server

    def save(self, user):
        """
        Save the chosen subdomain and mark the server as chosen.
        """
        subdomain = self.cleaned_data["subdomain"]
        server = self.cleaned_data["server"]
        affiliate_commission = self.cleaned_data["affiliate_commission"]
        profile = ServerOwner.objects.get(user=user)
        profile.subdomain = subdomain
        profile.affiliate_commission = affiliate_commission
        profile.save()
        server.choice_server = True
        server.save()


class PlanForm(forms.ModelForm):
    """
    Form for creating a Stripe Product.
    """

    interval_count = forms.IntegerField(
        label="Plan Duration in Months",
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Enter a value between 1 to 12",
                "class": "form-control",
            }
        ),
        required=True,
    )

    class Meta:
        model = StripePlan
        fields = [
            "name",
            "amount",
            "interval_count",
            "description",
            "discord_role_id",
            "permission_description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "discord_role_id": forms.TextInput(attrs={"class": "form-control"}),
            "permission_description": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_amount(self):
        """
        Validate that the amount is a positive value.
        """
        amount = self.cleaned_data.get("amount")
        if amount <= 0:
            raise forms.ValidationError("Amount must be a positive value.")
        return amount

    def clean_interval_count(self):
        """
        Validate that the interval_count is a positive value.
        """
        interval_count = self.cleaned_data.get("interval_count")
        if interval_count < 1 or interval_count > 12:
            raise forms.ValidationError("Interval count must be between 1 and 12.")
        return interval_count

    def clean_name(self):
        """
        Validate that the Plan name is unique for the Serverowner.
        """
        name = self.cleaned_data.get("name")
        if self.instance and self.instance.name == name:
            # Plan name remains the same, no need for uniqueness check
            return name
        if StripePlan.objects.filter(name=name).exists():
            raise forms.ValidationError("This name has already been chosen.")
        return name

    def clean_description(self):
        """
        Clean up the description field to remove excess whitespace.
        """
        description = self.cleaned_data.get("description")
        if description:
            description = re.sub(r"\s+", " ", description).strip()
        return description

    def clean_permission_description(self):
        """
        Clean up the permission_description field to remove excess whitespace.
        """
        permission_description = self.cleaned_data.get("permission_description")
        if permission_description:
            permission_description = re.sub(r"\s+", " ", permission_description).strip()
        return permission_description


class PaymentDetailForm(forms.ModelForm):
    class Meta:
        model = PaymentDetail
        fields = ["body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        }
