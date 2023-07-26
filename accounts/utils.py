import hashlib
import hmac

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def mk_paginator(request, items, num_items):
    """
    Function to paginate querysets.

    :param request: The current request object
    :param items: The queryset to be paginated
    :param num_items: The number of items to be displayed per page
    :return: A paginated queryset
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
    key_bytes = bytes(api_secret_key, "latin-1")
    data_bytes = bytes(data, "latin-1")
    return hmac.new(key_bytes, data_bytes, hashlib.sha512).hexdigest()
