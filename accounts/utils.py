import hashlib
import hmac

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def mk_paginator(request, items, num_items):
    """Create a paginator for querysets.

    Args:
        request (HttpRequest): The current request object.
        items (QuerySet): The queryset to be paginated.
        num_items (int): The number of items to be displayed per page.

    Returns:
        Page: A paginated queryset representing the current page.
    """
    paginator = Paginator(items, num_items)
    page = request.GET.get("page", 1)
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, return the first page.
        items = paginator.page(1)
    except EmptyPage:
        # If page is out of range, return the last page of results.
        items = paginator.page(paginator.num_pages)
    return items


def create_hmac_signature(data, api_secret_key):
    """Create an HMAC signature for the provided data.

    Args:
        data (str): The data for which the HMAC signature is to be created.
        api_secret_key (str): The API secret key used for creating the HMAC signature.

    Returns:
        str: The hexadecimal representation of the HMAC signature.
    """
    key_bytes = bytes(api_secret_key, "latin-1")
    data_bytes = bytes(data, "latin-1")
    return hmac.new(key_bytes, data_bytes, hashlib.sha512).hexdigest()
