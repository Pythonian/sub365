from django.shortcuts import redirect


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

        If the server owner does not have a subdomain, redirects to the 'choose_name' view.

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
            return redirect('choose_name')
        return view_func(request, *args, **kwargs)

    return wrapped_view
