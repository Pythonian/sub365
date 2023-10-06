from functools import wraps

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect


def onboarding_completed(view_func):
    """Decorator to check for user onboarding status.

    Args:
        view_func (function): The view function to be wrapped.

    Returns:
        function: Wrapped view function that performs redirection as needed.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            serverowner = request.user.serverowner
            stripe_account_id = serverowner.stripe_account_id

            # Check if subdomain is missing
            if not serverowner.subdomain:
                return redirect("onboarding")

            # Check if stripe onboarding is not completed
            if stripe_account_id and not serverowner.stripe_onboarding:
                return redirect("collect_user_info")

            # When a user onboards with stripe and not coinpayments?
            if serverowner.stripe_onboarding and (
                not serverowner.coinpayment_api_public_key or not serverowner.coinpayment_api_secret_key
            ):
                return view_func(request, *args, **kwargs)
            elif not serverowner.coinpayment_api_public_key and not serverowner.coinpayment_api_secret_key:
                return redirect("onboarding_crypto")

        except ObjectDoesNotExist:
            # Handle the case where the ServerOwner object does not exist for the user
            messages.error(request, "You have trespassed into forbidden territory.")
            return redirect("index")

        return view_func(request, *args, **kwargs)

    return wrapper
