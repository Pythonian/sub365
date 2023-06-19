from django.http import HttpResponse
import json
import stripe
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def stripe_webhook(request):
    """
    Webhook endpoint to handle Stripe events.
    """

    payload = request.body
    event = None

    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        # Invalid payload
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
