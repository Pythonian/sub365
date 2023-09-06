from functools import wraps

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect

import stripe

from .models import ServerOwner


def redirect_if_no_subdomain(view_func):
    """
    Decorator that redirects users to the onboarding page if they don't have a subdomain set.

    Args:
        view_func (function): The view function to be wrapped.

    Returns:
        function: Wrapped view function that performs redirection if subdomain is missing.
    """
    def wrapped_view(request, *args, **kwargs):
        try:
            if not request.user.serverowner.subdomain:
                return redirect("onboarding")
        except ObjectDoesNotExist:
            # Handle the case where the ServerOwner object does not exist for the user
            messages.error(request, "You have trespassed into forbidden territory.")
            return redirect("index")
        return view_func(request, *args, **kwargs)

    return wrapped_view

# def onboarding_completed(view_func):
#     """
#     Decorator that checks if stripe onboarding is completed for a user.

#     Args:
#         view_func (function): The view function to be wrapped.

#     Returns:
#         function: Wrapped view function that checks if onboarding is completed.
#     """

#     @wraps(view_func)
#     def wrapper(request, *args, **kwargs):
#         serverowner = request.user.serverowner

#         if not serverowner.stripe_onboarding:
#             return redirect("collect_user_info")

#         return view_func(request, *args, **kwargs)

#     return wrapper

def onboarding_completed(view_func):
    """
    Decorator that checks if onboarding is completed for a user.

    Args:
        view_func (function): The view function to be wrapped.

    Returns:
        function: Wrapped view function that checks if onboarding is completed.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        serverowner = get_object_or_404(ServerOwner, user=request.user)
        stripe_account_id = serverowner.stripe_account_id

        if stripe_account_id:
            # Retrieve the user's Stripe account
            stripe_account = stripe.Account.retrieve(stripe_account_id)
            # Check if charges are enabled and details are submitted
            charges_enabled = stripe_account.charges_enabled
            details_submitted = stripe_account.details_submitted
            if not charges_enabled and not details_submitted:
                return redirect("collect_user_info")

        return view_func(request, *args, **kwargs)

    return wrapper
