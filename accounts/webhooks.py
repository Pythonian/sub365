import logging

import stripe
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import AffiliateInvitee, AffiliatePayment, ServerOwner, Subscription
from .tasks import send_payment_failed_email

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    """Webhook endpoint to handle Stripe events."""
    # Verify the webhook event using the Stripe signature
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        logger.exception("An error occurred during a Stripe API call: %s", str(e))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.exception("An error occurred during a Stripe API call: %s", str(e))
        return HttpResponse(status=400)

    if event.type == "invoice.paid":
        subscription_id = event.data.object.subscription

        try:
            subscription = Subscription.objects.get(subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            # Handle the case where the subscription is not found
            logger.error(f"Subscription not found for ID: {subscription_id}")
            return HttpResponse(status=404)

        # Check if the payment was successful
        if event.data.object.status == "paid":
            with transaction.atomic():
                # Payment was successful
                subscription.status = Subscription.SubscriptionStatus.ACTIVE
                subscription.subscription_date = timezone.now()
                interval_count = subscription.plan.interval_count
                subscription.expiration_date = timezone.now() + relativedelta(months=interval_count)
                subscription.save()

                subscriber = subscription.subscriber
                try:
                    affiliateinvitee = AffiliateInvitee.objects.get(invitee_discord_id=subscriber.discord_id)
                    affiliatepayment = AffiliatePayment.objects.create(  # noqa
                        serverowner=subscriber.subscribed_via,
                        affiliate=affiliateinvitee.affiliate,
                        subscriber=subscriber,
                        amount=affiliateinvitee.get_affiliate_commission_payment(),
                    )

                    affiliateinvitee.affiliate.update_last_payment_date()
                    affiliateinvitee.affiliate.pending_commissions = (
                        F("pending_commissions") + affiliateinvitee.get_affiliate_commission_payment()
                    )
                    affiliateinvitee.affiliate.save()

                    subscriber.subscribed_via.total_pending_commissions = (
                        F("total_pending_commissions") + affiliateinvitee.get_affiliate_commission_payment()
                    )
                    subscriber.subscribed_via.save()

                except ObjectDoesNotExist:
                    affiliateinvitee = None

                # Increment the subscriber count for the plan
                plan = subscription.plan
                plan.subscriber_count = F("subscriber_count") + 1
                plan.save()

    elif event.type == "invoice.payment_failed":
        subscription_id = event.data.object.subscription

        try:
            subscription = Subscription.objects.get(subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            # Handle the case where the subscription is not found
            logger.error(f"Subscription not found for ID: {subscription_id}")
            return HttpResponse(status=404)

        # Delete the subscription from the database
        subscription.delete()

        # Send a notification to the subscriber
        send_payment_failed_email.delay(subscription.subscriber.email)

    elif event.type == "account.updated":
        account = event.data.object
        charges_enabled = account.charges_enabled
        payouts_enabled = account.payouts_enabled
        details_submitted = account.details_submitted

        # Update Serverowner's stripe_onboarding field if conditions are met
        try:
            serverowner = ServerOwner.objects.get(stripe_account_id=account.id)
            if charges_enabled and payouts_enabled and details_submitted:
                serverowner.stripe_onboarding = True
                serverowner.save()
        except ServerOwner.DoesNotExist:
            pass

    return HttpResponse(status=200)
