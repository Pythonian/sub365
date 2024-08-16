"""Background tasks."""

import logging

import requests
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from .models import AffiliateInvitee, AffiliatePayment, CoinSubscription
from .utils import create_hmac_signature

logger = logging.getLogger(__name__)


@shared_task(name="check_coin_transaction_status")
def check_coin_transaction_status():
    """Periodic task to check the status of coin transactions for pending coin subscriptions.

    Raises:
        Exception: If an unexpected error occurs during the processing of coin transactions.
    """
    try:
        pending_subscriptions = CoinSubscription.pending_subscriptions.all()

        for coin_subscription in pending_subscriptions:
            try:
                endpoint = "https://www.coinpayments.net/api.php"
                data = (
                    f"version=1&cmd=get_tx_info&txid={coin_subscription.subscription_id}"
                    f"&key={coin_subscription.subscribed_via.coinpayment_api_public_key}&format=json"
                )
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "HMAC": create_hmac_signature(
                        data,
                        coin_subscription.subscribed_via.coinpayment_api_secret_key,
                    ),
                }
                response = requests.post(endpoint, data=data, headers=headers)
                result = response.json().get("result")

                if isinstance(result, dict):
                    status = result.get("status")
                    if (
                        status == 100
                        and coin_subscription.status
                        == CoinSubscription.SubscriptionStatus.PENDING
                    ):
                        with transaction.atomic():
                            coin_subscription.status = (
                                CoinSubscription.SubscriptionStatus.ACTIVE
                            )
                            coin_subscription.subscription_date = timezone.now()
                            interval_count = coin_subscription.plan.interval_count
                            coin_subscription.expiration_date = (
                                timezone.now() + relativedelta(months=interval_count)
                            )
                            coin_subscription.save()

                            subscriber = coin_subscription.subscriber

                            try:
                                affiliate_invitee = AffiliateInvitee.objects.get(
                                    invitee_discord_id=subscriber.discord_id,
                                )
                                AffiliatePayment.objects.create(
                                    serverowner=subscriber.subscribed_via,
                                    affiliate=affiliate_invitee.affiliate,
                                    subscriber=subscriber,
                                    amount=affiliate_invitee.get_affiliate_commission_payment(),
                                    coin_amount=affiliate_invitee.get_affiliate_coin_commission_payment(),
                                )

                                affiliate_invitee.affiliate.pending_coin_commissions = (
                                    F("pending_coin_commissions")
                                    + affiliate_invitee.get_affiliate_coin_commission_payment()
                                )
                                affiliate_invitee.affiliate.pending_commissions = (
                                    F("pending_commissions")
                                    + affiliate_invitee.get_affiliate_commission_payment()
                                )
                                affiliate_invitee.affiliate.save()

                                subscriber.subscribed_via.total_coin_pending_commissions = (
                                    F("total_coin_pending_commissions")
                                    + affiliate_invitee.get_affiliate_coin_commission_payment()
                                )
                                subscriber.subscribed_via.total_pending_commissions = (
                                    F("total_pending_commissions")
                                    + affiliate_invitee.get_affiliate_commission_payment()
                                )
                                subscriber.subscribed_via.save()

                            except AffiliateInvitee.DoesNotExist:
                                affiliate_invitee = None

                            plan = coin_subscription.plan
                            plan.subscriber_count = F("subscriber_count") + 1
                            plan.subscription_earnings = (
                                F("subscription_earnings") + plan.amount
                            )
                            plan.save()

                            subscriber.subscribed_via.total_earnings = (
                                F("total_earnings") + plan.amount
                            )
                            subscriber.subscribed_via.save()

                    elif status == -1:
                        # Transaction failed, Delete the subscription object
                        coin_subscription.delete()
                    else:
                        msg = f"Transaction ID: {coin_subscription.subscription_id}, status: {status}"
                        logger.warning(msg)
                else:
                    logger.warning("Unexpected format for 'result': %s", result)
            except ObjectDoesNotExist:
                coin_subscription = None
            except requests.exceptions.RequestException:
                logger.exception("CoinPayments API request failed")
            except (ValueError, KeyError):
                logger.exception("Failed to parse CoinPayments API response")
            except Exception:
                logger.exception("An unexpected error occurred")

    except Exception:
        logger.exception("An unexpected error occurred")


@shared_task(name="check_and_mark_expired_subscriptions")
def check_and_mark_expired_subscriptions():
    """Periodic task to check and mark expired coin subscriptions."""
    now = timezone.now()
    expired_subscriptions = CoinSubscription.active_subscriptions.filter(
        expiration_date__lte=now,
    )

    for subscription in expired_subscriptions:
        subscription.status = CoinSubscription.SubscriptionStatus.EXPIRED
        subscription.save()

        # Render the email content
        context = {"subscriber": subscription.subscriber}
        subject = render_to_string("emails/subscription_expired_subject.txt").strip()
        text_content = render_to_string("emails/subscription_expired_body.txt", context)
        html_content = render_to_string(
            "emails/subscription_expired_body.html",
            context,
        )

        # Send the email
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [subscription.subscriber.email]
        email = EmailMultiAlternatives(
            subject,
            text_content,
            from_email,
            recipient_list,
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


@shared_task
def send_affiliate_email(affiliate_email, affiliate, serverowner, commission_amount):
    """Task to send an email notification to an affiliate about received commission.

    Args:
        affiliate_email (str): The email address of the affiliate.
        affiliate (str): The name of the affiliate.
        serverowner (str): The name of the server owner.
        commission_amount (float): The amount of commission received.
    """
    subject = render_to_string(
        "emails/affiliate_commission_payment_subject.txt",
    ).strip()
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [affiliate_email]

    # Render the templates
    context = {
        "affiliate": affiliate,
        "serverowner": serverowner,
        "commission_amount": commission_amount,
    }
    html_content = render_to_string("emails/affiliate_commission_body.html", context)
    text_content = render_to_string("emails/affiliate_commission_body.txt", context)

    # Send the email
    email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.send()


@shared_task
def send_payment_failed_email(subscriber_email):
    """Task to send an email notification to a subscriber about a failed payment.

    Args:
        subscriber_email (str): The email address of the subscriber.
    """
    subject = render_to_string("emails/subscription_payment_failed_subject.txt").strip()
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [subscriber_email]

    html_content = render_to_string(
        "emails/subscription_payment_failed_body.html",
    )
    text_content = render_to_string(
        "emails/subscription_payment_failed_body.txt",
    )

    # Send the email
    email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.send()
