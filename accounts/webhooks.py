import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import stripe

from .models import Subscription  # noqa

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
        event = stripe.Webhook.construct_event(  # noqa
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

    # if event.type == "invoice.payment_succeeded" or event.type == "invoice.paid":
    #     # Invoice payment succeeded for the subscription renewal
    #     subscription_id = event.data.object.lines.data[0].subscription
    #     try:
    #         subscription = Subscription.objects.get(subscription_id=subscription_id)
    #         # Update the Subscription object with the new expiration date and subscription_date
    #         current_period_end = event.data.object.period_end
    #         expiration_date = timezone.datetime.fromtimestamp(current_period_end)
    #         subscription.expiration_date = expiration_date
    #         subscription.subscription_date = (
    #             expiration_date  # Update subscription_date with the renewal date
    #         )
    #         subscription.save()
    #     except Subscription.DoesNotExist:
    #         logger.error(
    #             "Subscription not found for subscription_id: %s", subscription_id
    #         )
    #     except stripe.error.StripeError as e:
    #         logger.exception("An error occurred during a Stripe API call: %s", str(e))

    return HttpResponse(status=200)
