import logging

import requests
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
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
                data = f"version=1&cmd=get_tx_info&txid={coin_subscription.subscription_id}&key={coin_subscription.subscribed_via.coinpayment_api_public_key}&format=json"
                header = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "HMAC": create_hmac_signature(data, coin_subscription.subscribed_via.coinpayment_api_secret_key),
                }
                response = requests.post(endpoint, data=data, headers=header)
                result = response.json().get("result")

                if isinstance(result, dict):
                    status = result.get("status")
                    if status == 100 and coin_subscription.status == CoinSubscription.SubscriptionStatus.PENDING:
                        with transaction.atomic():
                            coin_subscription.status = CoinSubscription.SubscriptionStatus.ACTIVE
                            coin_subscription.subscription_date = timezone.now()
                            interval_count = coin_subscription.plan.interval_count
                            coin_subscription.expiration_date = timezone.now() + relativedelta(months=interval_count)
                            coin_subscription.save()

                            subscriber = coin_subscription.subscriber

                            try:
                                affiliateinvitee = AffiliateInvitee.objects.get(
                                    invitee_discord_id=subscriber.discord_id
                                )
                                AffiliatePayment.objects.create(
                                    serverowner=subscriber.subscribed_via,
                                    affiliate=affiliateinvitee.affiliate,
                                    subscriber=subscriber,
                                    amount=affiliateinvitee.get_affiliate_commission_payment(),
                                    coin_amount=affiliateinvitee.get_affiliate_coin_commission_payment(),
                                )

                                affiliateinvitee.affiliate.update_last_payment_date()
                                affiliateinvitee.affiliate.pending_coin_commissions = (
                                    F("pending_coin_commissions")
                                    + affiliateinvitee.get_affiliate_coin_commission_payment()
                                )
                                affiliateinvitee.affiliate.pending_commissions = (
                                    F("pending_commissions") + affiliateinvitee.get_affiliate_commission_payment()
                                )
                                affiliateinvitee.affiliate.save()

                                subscriber.subscribed_via.total_coin_pending_commissions = (
                                    F("total_coin_pending_commissions")
                                    + affiliateinvitee.get_affiliate_coin_commission_payment()
                                )
                                subscriber.subscribed_via.total_pending_commissions = (
                                    F("total_pending_commissions")
                                    + affiliateinvitee.get_affiliate_commission_payment()
                                )
                                subscriber.subscribed_via.save()

                            except AffiliateInvitee.DoesNotExist:
                                affiliateinvitee = None

                            # Increment the subscriber count for the plan
                            plan = coin_subscription.plan
                            plan.subscriber_count = F("subscriber_count") + 1
                            plan.save()
                    elif status == -1:
                        # Transaction failed, Delete the subscription object
                        coin_subscription.delete()
                    else:
                        msg = f"Transaction ID: {coin_subscription.subscription_id}, status: {status}"
                        logger.warning(msg)
                else:
                    logger.warning(f"Unexpected format for 'result': {result}")
            except ObjectDoesNotExist:
                coin_subscription = None
            except requests.exceptions.RequestException as e:
                logger.exception(f"Coinbase API request failed: {e}")
            except (ValueError, KeyError) as e:
                logger.exception(f"Failed to parse Coinbase API response: {e}")
            except Exception as e:
                logger.exception(f"An unexpected error occurred: {e}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


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

        # Send email to the subscriber
        subject = "Sub365.co: Your Subscription has Expired"
        message = f"Dear {subscription.subscriber}, your subscription has expired. You can visit your account to start a new subscription today.\n\nBest regards,\nwww.sub365.co"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [subscription.subscriber.email]
        send_mail(subject, message, from_email, recipient_list)


@shared_task
def send_affiliate_email(affiliate_email, affiliate, serverowner, commission_amount):
    subject = "Sub365.co: Affiliate Commission Received"
    message = f"Dear {affiliate}, \n\nYou have just received an affiliate commission of ${commission_amount} from {serverowner}.\n\nBest regards,\nwww.sub365.co"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [affiliate_email]
    send_mail(subject, message, from_email, recipient_list)


@shared_task
def send_payment_failed_email(subscriber_email):
    subject = "Sub365.co: Subscription Payment Failed Notification"
    message = "Your subscription payment has failed. Please visit your dashboard and try again."
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [subscriber_email]
    send_mail(subject, message, from_email, recipient_list)
