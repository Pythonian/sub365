import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

import stripe

from .models import Subscription

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook endpoint to handle Stripe events.
    """

    # Verify the webhook event using the Stripe signature
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        logger.exception("An error occurred during a Stripe API call: %s", str(e))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.exception("An error occurred during a Stripe API call: %s", str(e))
        return HttpResponse(status=400)

    # Handle the (subscription.canceled) event
    if event.type == "customer.subscription.deleted":
        subscription_id = event.data.object.id
        # Retrieve the Subscription object from your database
        try:
            subscription = Subscription.objects.get(
                subscription_id=subscription_id
            )  # noqa
        except stripe.error.StripeError as e:
            logger.exception("An error occurred during a Stripe API call: %s", str(e))
            pass

        # Update the Subscription object
        subscription.status = Subscription.SubscriptionStatus.CANCELED
        subscription.save()

    return HttpResponse(status=200)
