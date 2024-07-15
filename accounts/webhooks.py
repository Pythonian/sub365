"""Stripe webhook endpoint for real-time event notifications."""

import logging
from datetime import timezone

import stripe
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    AffiliateInvitee,
    AffiliatePayment,
    ServerOwner,
    StripeSubscription,
)
from .tasks import send_payment_failed_email

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    """Handle incoming Stripe webhook events.

    This function verifies the webhook event, processes different types of events,
    and updates relevant database records accordingly.

    Args:
        request (HttpRequest): The HTTP request object containing the webhook payload.

    Returns:
        HttpResponse: HTTP response indicating the status of webhook processing.
            - 200 OK if the webhook event was processed successfully.
            - 400 Bad Request if there was an error verifying the webhook event.
    """
    payload = request.body
    sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        # Invalid payload
        msg = f"Error verifying webhook payload: {e}"
        logger.exception(msg)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        msg = f"Error verifying webhook signature: {e}"
        logger.exception(msg)
        return HttpResponse(status=400)

    if event.type == "invoice.paid":
        # Process payment success event
        subscription_id = event.data.object.subscription
        try:
            subscription = StripeSubscription.objects.get(
                subscription_id=subscription_id,
            )
        except StripeSubscription.DoesNotExist:
            subscription = None

        if event.data.object.status == "paid":
            with transaction.atomic():
                # Update subscription status and dates
                subscription.status = StripeSubscription.SubscriptionStatus.ACTIVE
                if subscription.subscription_date is None:
                    subscription.subscription_date = timezone.datetime.fromtimestamp(
                        event.data.object.created,
                        tz=timezone.utc,
                    )
                current_period_end = event.data.object.lines.data[0].period.end
                expiration_date = timezone.datetime.fromtimestamp(
                    current_period_end,
                    tz=timezone.utc,
                )
                subscription.expiration_date = expiration_date
                subscription.save()

                # Handle affiliate commission payment and updates
                subscriber = subscription.subscriber
                try:
                    affiliateinvitee = AffiliateInvitee.objects.get(
                        invitee_discord_id=subscriber.discord_id,
                    )
                    AffiliatePayment.objects.create(
                        serverowner=subscriber.subscribed_via,
                        affiliate=affiliateinvitee.affiliate,
                        subscriber=subscriber,
                        amount=affiliateinvitee.get_affiliate_commission_payment(),
                    )
                    affiliateinvitee.affiliate.pending_commissions = (
                        F("pending_commissions")
                        + affiliateinvitee.get_affiliate_commission_payment()
                    )
                    affiliateinvitee.affiliate.save()

                    subscriber.subscribed_via.total_pending_commissions = (
                        F("total_pending_commissions")
                        + affiliateinvitee.get_affiliate_commission_payment()
                    )
                    subscriber.subscribed_via.save()

                except ObjectDoesNotExist:
                    affiliateinvitee = None

                # Update plan statistics
                plan = subscription.plan
                plan.subscriber_count = F("subscriber_count") + 1
                plan.subscription_earnings = F("subscription_earnings") + plan.amount
                plan.save()

                # Update server owner earnings
                subscriber.subscribed_via.total_earnings = (
                    F("total_earnings") + plan.amount
                )
                subscriber.subscribed_via.save()

    elif event.type == "invoice.payment_failed":
        # Handle payment failure event
        subscription_id = event.data.object.subscription
        try:
            subscription = StripeSubscription.objects.get(
                subscription_id=subscription_id,
            )
        except StripeSubscription.DoesNotExist:
            logger.exception("Subscription not found")
            return HttpResponse(status=404)

        if subscription.status == StripeSubscription.SubscriptionStatus.PENDING:
            # Delete new subscription if payment failed
            subscription.delete()
        else:
            # Mark renewal subscription as expired if payment failed
            subscription.status = StripeSubscription.SubscriptionStatus.EXPIRED
            subscription.expiration_date = timezone.now()
            subscription.save()

        # Send notification email to subscriber
        send_payment_failed_email.delay(subscription.subscriber.email)

    elif event.type == "account.updated":
        # Handle server owner onboarding status update event
        account = event.data.object
        charges_enabled = account.charges_enabled
        payouts_enabled = account.payouts_enabled
        details_submitted = account.details_submitted

        try:
            serverowner = ServerOwner.objects.get(stripe_account_id=account.id)
            if charges_enabled and payouts_enabled and details_submitted:
                serverowner.stripe_onboarding = True
                serverowner.save()
        except ServerOwner.DoesNotExist:
            pass

    return HttpResponse(status=200)
