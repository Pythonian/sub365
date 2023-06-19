from django.http import HttpResponse
from django.conf import settings
import json
import stripe
from django.views.decorators.csrf import csrf_exempt

from .models import StripePlan, Subscription


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook endpoint to handle Stripe events.
    """

    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event.type == "checkout.session.completed":
        session = event.data.object
        subscription_id = session.subscription

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            expiration_date = subscription.current_period_end
            # Handle the expiration date as needed
            # ...
        except stripe.error.StripeError as e:
            # Handle the error
            pass

    return HttpResponse(status=200)
