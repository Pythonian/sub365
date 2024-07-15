"""Form classes."""

import re

import coinaddrvalidator
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import AccessCode, CoinPlan, PaymentDetail, Server, ServerOwner, StripePlan


def forbidden_referralname_validator(value):
    """Validate that the referral name is not one of the forbidden names.

    Args:
        value (str): The referral name to validate.

    Raises:
        ValidationError: If the referral name is forbidden.
    """
    forbidden_names = [
        "accounts",
        "admin",
        "administrator",
        "affiliate",
        "delete",
        "disable",
        "feedback",
        "media",
        "root",
        "static",
        "sub365",
        "subscribe",
        "subscriber",
    ]
    if value.lower() in forbidden_names:
        msg = "You are not allowed to use this name."
        raise ValidationError(msg)


class Lowercase(forms.CharField):
    """Custom form field to convert values to lowercase."""

    def to_python(self, value):
        """Convert the input value to lowercase.

        Args:
            value (str): The input value.

        Returns:
            str: The input value converted to lowercase.
        """
        return value.lower()


class Uppercase(forms.CharField):
    """Custom form field to convert values to uppercase."""

    def to_python(self, value):
        """Convert the input value to uppercase.

        Args:
            value (str): The input value.

        Returns:
            str: The input value converted to uppercase.
        """
        return value.upper()


class OnboardingForm(forms.Form):
    """Form for choosing a server and referral name."""

    referral = Lowercase(
        min_length=4,
        max_length=20,
    )
    server = forms.ModelChoiceField(queryset=Server.objects.none())
    affiliate_commission = forms.IntegerField(
        min_value=1,
        max_value=99,
    )
    access_code = Uppercase(
        min_length=5,
        max_length=5,
    )

    def __init__(self, *args, **kwargs):
        """Form initialization.

        Initialize the form with the user and populate the server choices
        with servers of the current user.
        """
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["server"].queryset = Server.objects.filter(owner__user=user)
            self.fields["server"].empty_label = "Choose a server"
            self.fields["referral"].validators.append(forbidden_referralname_validator)

    def clean_referral(self):
        """Validate that the referral name is unique and meets the required pattern.

        Returns:
            str: The cleaned referral name.

        Raises:
            forms.ValidationError: If the referral name is not unique or doesn't match the pattern.
        """
        referral = self.cleaned_data.get("referral")
        if ServerOwner.objects.filter(subdomain__iexact=referral).exists():
            msg = "This referral name has already been chosen."
            raise forms.ValidationError(msg)
        if not re.match(r"^[a-z0-9_]+$", referral):
            msg = "Referral name can only contain lowercase letters, numbers, and hyphens."
            raise forms.ValidationError(msg)
        return referral

    def clean_affiliate_commission(self):
        """Validate that the affiliate commission is between 1 and 99.

        Returns:
            int: The cleaned affiliate commission.

        Raises:
            forms.ValidationError: If the affiliate commission is not between 1 and 99.
        """
        affiliate_commission = self.cleaned_data.get("affiliate_commission")
        if affiliate_commission < 1 or affiliate_commission > 99:
            msg = "Affiliate commission must be between 1 and 99."
            raise forms.ValidationError(msg)
        return affiliate_commission

    def clean_access_code(self):
        """Validate the access code and check if it has been used.

        Returns:
            str: The cleaned access code.

        Raises:
            forms.ValidationError: If the access code is invalid or has been used.
        """
        access_code = self.cleaned_data.get("access_code")
        try:
            access_code_obj = AccessCode.objects.get(code=access_code)
            if access_code_obj.is_used:
                msg = "Invalid code. Contact admin@sub365.co"
                raise forms.ValidationError(msg)
        except AccessCode.DoesNotExist as e:
            msg = "Invalid code. Contact admin@sub365.co"
            raise forms.ValidationError(msg) from e
        return access_code

    def save(self, user):
        """Save the form data, updating the serverowner and access code details.

        Args:
            user (User): The user saving the form.
        """
        referral = self.cleaned_data["referral"]
        server = self.cleaned_data["server"]
        affiliate_commission = self.cleaned_data["affiliate_commission"]

        serverowner = ServerOwner.objects.get(user=user)
        serverowner.subdomain = referral
        serverowner.affiliate_commission = affiliate_commission
        serverowner.save()

        server.choice_server = True
        server.save()

        access_code = self.cleaned_data["access_code"]
        code = AccessCode.objects.get(code=access_code)
        code.is_used = True
        code.used_by = serverowner
        code.date_used = timezone.now()
        code.save()


class CoinpaymentsOnboardingForm(forms.Form):
    """Form to enable serverowners add Coinpayment API keys."""

    coinpayment_api_secret_key = forms.CharField(
        max_length=255,
        required=True,
    )
    coinpayment_api_public_key = forms.CharField(
        max_length=255,
        required=True,
    )

    def clean(self):
        """Validate that the Coinpayment API keys are unique.

        Raises:
            forms.ValidationError: If one or both of the API keys already exist.
        """
        cleaned_data = super().clean()
        api_secret_key = cleaned_data.get("coinpayment_api_secret_key")
        api_public_key = cleaned_data.get("coinpayment_api_public_key")

        if (
            ServerOwner.objects.filter(
                coinpayment_api_secret_key=api_secret_key,
            ).exists()
            or ServerOwner.objects.filter(
                coinpayment_api_public_key=api_public_key,
            ).exists()
        ):
            msg = "One or both of the API keys already exist."
            raise forms.ValidationError(msg)


class StripePlanForm(forms.ModelForm):
    """Form for creating a Stripe Product."""

    class Meta:
        """Meta configuration for the StripePlanForm."""

        model = StripePlan
        fields = [
            "name",
            "amount",
            "interval_count",
            "description",
            "discord_role_id",
            "permission_description",
        ]

    def clean_amount(self):
        """Validate that the amount is a positive value.

        Returns:
            int: The cleaned amount.

        Raises:
            forms.ValidationError: If the amount is not positive.
        """
        amount = self.cleaned_data.get("amount")
        if amount <= 0:
            msg = "Amount must be a positive value."
            raise forms.ValidationError(msg)
        return amount

    def clean_interval_count(self):
        """Validate that the interval count is between 1 and 12.

        Returns:
            int: The cleaned interval count.

        Raises:
            forms.ValidationError: If the interval count is not between 1 and 12.
        """
        interval_count = self.cleaned_data.get("interval_count")
        if interval_count < 1 or interval_count > 12:
            msg = "Interval count must be between 1 and 12."
            raise forms.ValidationError(msg)
        return interval_count

    def clean_name(self):
        """Validate that the plan name is unique for the Serverowner.

        Returns:
            str: The cleaned plan name.

        Raises:
            forms.ValidationError: If the plan name is not unique.
        """
        name = self.cleaned_data.get("name")
        if self.instance and self.instance.name == name:
            # Plan name remains the same, no need for uniqueness check
            return name
        if StripePlan.objects.filter(name__iexact=name).exists():
            msg = "This name has already been chosen."
            raise forms.ValidationError(msg)
        return name

    def clean_description(self):
        """Clean up the description field to remove excess whitespace.

        Returns:
            str: The cleaned description.
        """
        description = self.cleaned_data.get("description")
        if description:
            description = re.sub(r"\s+", " ", description).strip()
        return description

    def clean_permission_description(self):
        """Clean up the permission description field to remove excess whitespace.

        Returns:
            str: The cleaned permission description.
        """
        permission_description = self.cleaned_data.get("permission_description")
        if permission_description:
            permission_description = re.sub(r"\s+", " ", permission_description).strip()
        return permission_description


class CoinPlanForm(forms.ModelForm):
    """Form for creating a Coin plan."""

    class Meta:
        """Meta configuration for the CoinPlanForm."""

        model = CoinPlan
        fields = [
            "name",
            "amount",
            "interval_count",
            "description",
            "discord_role_id",
            "permission_description",
        ]

    def clean_amount(self):
        """Validate that the amount is a positive value.

        Returns:
            int: The cleaned amount.

        Raises:
            forms.ValidationError: If the amount is not positive.
        """
        amount = self.cleaned_data.get("amount")
        if amount <= 0:
            msg = "Amount must be a positive value."
            raise forms.ValidationError(msg)
        return amount

    def clean_interval_count(self):
        """Validate that the interval count is between 1 and 12.

        Returns:
            int: The cleaned interval count.

        Raises:
            forms.ValidationError: If the interval count is not between 1 and 12.
        """
        interval_count = self.cleaned_data.get("interval_count")
        if interval_count < 1 or interval_count > 12:
            msg = "Interval count must be between 1 and 12."
            raise forms.ValidationError(msg)
        return interval_count

    def clean_name(self):
        """Validate that the plan name is unique for the Serverowner.

        Returns:
            str: The cleaned plan name.

        Raises:
            forms.ValidationError: If the plan name is not unique.
        """
        name = self.cleaned_data.get("name")
        if self.instance and self.instance.name == name:
            # Plan name remains the same, no need for uniqueness check
            return name
        if CoinPlan.objects.filter(name__iexact=name).exists():
            msg = "This name has already been chosen."
            raise forms.ValidationError(msg)
        return name

    def clean_description(self):
        """Clean up the description field to remove excess whitespace.

        Returns:
            str: The cleaned description.
        """
        description = self.cleaned_data.get("description")
        if description:
            description = re.sub(r"\s+", " ", description).strip()
        return description

    def clean_permission_description(self):
        """Clean up the permission description field to remove excess whitespace.

        Returns:
            str: The cleaned permission description.
        """
        permission_description = self.cleaned_data.get("permission_description")
        if permission_description:
            permission_description = re.sub(r"\s+", " ", permission_description).strip()
        return permission_description


class StripePaymentDetailForm(forms.ModelForm):
    """Form for affiliates to add Stripe payment details."""

    class Meta:
        """Meta configuration for the StripePaymentDetailForm."""

        model = PaymentDetail
        fields = ["body"]


class CoinPaymentDetailForm(forms.ModelForm):
    """Form for affiliates to add a Litecoin payment address."""

    class Meta:
        """Meta configuration for the CoinPaymentDetailForm."""

        model = PaymentDetail
        fields = ["litecoin_address"]

    def clean_litecoin_address(self):
        """Validate the Litecoin address.

        Returns:
            str: The cleaned Litecoin address.

        Raises:
            forms.ValidationError: If the Litecoin address is invalid.
        """
        litecoin_address = self.cleaned_data.get("litecoin_address")
        if not coinaddrvalidator.validate("litecoin", litecoin_address):
            msg = "Invalid Litecoin address. Please crosscheck."
            raise forms.ValidationError(msg)
        return litecoin_address
