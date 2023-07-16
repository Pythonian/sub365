from django.shortcuts import redirect
import stripe
from django.shortcuts import get_object_or_404
from accounts.models import ServerOwner
from functools import wraps


def redirect_if_no_subdomain(view_func):
    """
    Decorator to redirect if the server owner does not have a subdomain.

    Args:
        view_func (function): The view function to be wrapped.

    Returns:
        function: The wrapped view function.

    Example Usage:
        @redirect_if_no_subdomain
        def my_view(request):
            # Your view code here
            ...
    """

    def wrapped_view(request, *args, **kwargs):
        """
        Wrapped view function to check if the server owner has a subdomain.

        If the server owner does not have a subdomain, redirects to the 'onboarding' view.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response returned by the view function.

        Raises:
            None.
        """
        if not request.user.serverowner.subdomain:
            return redirect("onboarding")
        return view_func(request, *args, **kwargs)

    return wrapped_view


def check_stripe_onboarding(view_func):
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
