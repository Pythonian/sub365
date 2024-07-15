"""Module containing decorators for managing user onboarding and authentication."""

from functools import wraps

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect


def onboarding_completed(view_func):
    """Decorator to check if user's onboarding is completed.

    Redirects users based on their onboarding status.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """Wrapper function to check onboarding status before executing the view."""
        try:
            serverowner = request.user.serverowner

            # Check if referral name is missing
            if not serverowner.subdomain:
                return redirect("onboarding")

            # Check if stripe onboarding is not completed
            if serverowner.stripe_account_id and not serverowner.stripe_onboarding:
                return redirect("collect_user_info")

            # Handle when a user onboards with stripe and not coinpayments
            if serverowner.stripe_onboarding and (
                not serverowner.coinpayment_api_public_key
                or not serverowner.coinpayment_api_secret_key
            ):
                return view_func(request, *args, **kwargs)
            # Check when a user neither has the api keys set
            elif (
                not serverowner.coinpayment_api_public_key
                and not serverowner.coinpayment_api_secret_key
            ):
                return redirect("onboarding_crypto")

        except ObjectDoesNotExist:
            # Handle the case where the ServerOwner object does not exist for the user
            messages.error(request, "You have trespassed into forbidden territory.")
            return redirect("index")

        return view_func(request, *args, **kwargs)

    return wrapper


def redirect_authenticated_user(view_func):
    """Decorator to redirect authenticated users.

    Redirects authenticated users to the dashboard view.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """Wrapper function to redirect authenticated users before executing the view."""
        if request.user.is_authenticated:
            return redirect("dashboard_view")
        return view_func(request, *args, **kwargs)

    return wrapper


def stripe_onboarding_required(view_func):
    """Decorator to check stripe onboarding status.

    Redirects users to the dashboard if they haven't onboarded via stripe.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        """Wrapper function to check stripe onboarding status before executing the view."""
        try:
            serverowner = request.user.serverowner
            if serverowner.coinpayment_onboarding:
                return redirect("dashboard")
        except ObjectDoesNotExist:
            # Handle the case where the ServerOwner object does not exist for the user
            messages.error(request, "You have trespassed into forbidden territory.")
            return redirect("index")
        return view_func(request, *args, **kwargs)

    return wrapper
