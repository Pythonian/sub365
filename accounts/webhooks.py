import datetime
from django.http import HttpResponse
from django.conf import settings
import json
import stripe
from django.views.decorators.csrf import csrf_exempt

from .models import StripePlan, Subscription, Subscriber


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
            # Create or update the Subscription object
            subscriber = Subscriber.objects.get(user__stripe_customer_id=session.customer)
            subscription_obj, _ = Subscription.objects.get_or_create(
                subscriber=subscriber,
                session_id=session.id,
                defaults={
                    "subscription_id": subscription_id,
                    "expiration_date": datetime.fromtimestamp(expiration_date),
                    "status": Subscription.SubscriptionStatus.PENDING,
                }
            )
        except stripe.error.StripeError as e:
            # Handle the error
            pass

    elif event.type == "customer.subscription.created":
        subscription = event.data.object
        subscription_id = subscription.id

        try:
            # Update the Subscription object with the subscription ID
            subscription_obj = Subscription.objects.get(session_id=subscription_id)
            subscription_obj.subscription_id = subscription_id
            subscription_obj.save()
        except Subscription.DoesNotExist:
            # Handle the error
            pass

    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        subscription_id = subscription.id

        try:
            # Update the Subscription object based on the updated subscription details
            subscription_obj = Subscription.objects.get(subscription_id=subscription_id)
            # Update relevant fields as per your subscription workflow
            subscription_obj.status = Subscription.SubscriptionStatus.ACTIVE
            subscription_obj.save()
        except Subscription.DoesNotExist:
            # Handle the error
            pass

    elif event.type == "payment_intent.succeeded":
        payment_intent = event.data.object
        subscription_id = payment_intent.subscription

        try:
            # Update the Subscription object to set its status as "Active"
            subscription_obj = Subscription.objects.get(subscription_id=subscription_id)
            subscription_obj.status = Subscription.SubscriptionStatus.ACTIVE
            subscription_obj.save()
        except Subscription.DoesNotExist:
            # Handle the error
            pass

    return HttpResponse(status=200)


# @csrf_exempt
# def stripe_webhook(request):
#     """
#     Webhook endpoint to handle Stripe events.
#     """

#     payload = request.body
#     sig_header = request.META['HTTP_STRIPE_SIGNATURE']
#     event = None

#     try:
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
#         )
#     except ValueError as e:
#         # Invalid payload
#         return HttpResponse(status=400)
#     except stripe.error.SignatureVerificationError as e:
#         # Invalid signature
#         return HttpResponse(status=400)

#     # Handle the event
#     if event.type == "payment_intent.succeeded":
#         session = event.data.object
#         subscription_id = session.subscription
#         customer_id = session.customer

#         # try:
#         #     subscription = stripe.Subscription.retrieve(subscription_id)
#         #     expiration_date = subscription.current_period_end
#         # except stripe.error.StripeError as e:
#         #     # Handle the error
#         #     pass
#         try:
#             subscription_info = stripe.Subscription.retrieve(subscription_id)
#             expiration_date = datetime.fromtimestamp(subscription_info.current_period_end)

#             # Update the subscription object
#             subscription = Subscription.objects.get(subscription_id=subscription_id)
#             subscription.expiration_date = expiration_date
#             subscription.customer_id = customer_id
#             subscription.status = Subscription.SubscriptionStatus.ACTIVE
#             subscription.save()
#         except stripe.error.StripeError as e:
#             # Handle the error
#             pass

#     return HttpResponse(status=200)
