import logging
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail

import requests
from celery import shared_task

from .emails import send_coin_subscription_failure_email
from .models import (
    Affiliate,
    AffiliateInvitee,
    AffiliatePayment,
    CoinSubscription,
    ServerOwner,
)
from .utils import create_hmac_signature

logger = logging.getLogger(__name__)


@shared_task(name="check_coin_transaction_status")
def check_coin_transaction_status():
    try:
        pending_subscriptions = CoinSubscription.objects.filter(
            status=CoinSubscription.SubscriptionStatus.INACTIVE
        )

        for coin_subscription in pending_subscriptions:
            try:
                endpoint = "https://www.coinpayments.net/api.php"
                data = f"version=1&cmd=get_tx_info&txid={coin_subscription.subscription_id}&key={coin_subscription.subscribed_via.coinbase_api_public_key}&format=json"
                header = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "HMAC": create_hmac_signature(
                        data, coin_subscription.subscribed_via.coinbase_api_secret_key
                    ),
                }
                response = requests.post(endpoint, data=data, headers=header)
                result = response.json()["result"]
                if isinstance(result, dict):
                    if result.get("status") == 100:
                        with transaction.atomic():
                            if coin_subscription.status == CoinSubscription.SubscriptionStatus.INACTIVE:
                                coin_subscription.status = CoinSubscription.SubscriptionStatus.ACTIVE
                                coin_subscription.subscription_date = timezone.now()
                                interval_count = coin_subscription.plan.interval_count
                                coin_subscription.expiration_date = timezone.now() + relativedelta(
                                    months=interval_count
                                )
                                coin_subscription.save()

                                subscriber = coin_subscription.subscriber

                                try:
                                    affiliateinvitee = AffiliateInvitee.objects.get(
                                        invitee_discord_id=subscriber.discord_id
                                    )
                                    affiliatepayment = AffiliatePayment.objects.create(  # noqa
                                        serverowner=subscriber.subscribed_via,
                                        affiliate=affiliateinvitee.affiliate,
                                        subscriber=subscriber,
                                        amount=affiliateinvitee.get_affiliate_coin_commission_payment(),
                                    )

                                    affiliateinvitee.affiliate.update_last_payment_date()
                                    affiliateinvitee.affiliate.pending_coin_commissions = (
                                        F("pending_coin_commissions")
                                        + affiliateinvitee.get_affiliate_coin_commission_payment()
                                    )
                                    affiliateinvitee.affiliate.save()

                                    subscriber.subscribed_via.total_coin_pending_commissions = (
                                        F("total_coin_pending_commissions")
                                        + affiliateinvitee.get_affiliate_coin_commission_payment()
                                    )
                                    subscriber.subscribed_via.save()

                                except AffiliateInvitee.DoesNotExist:
                                    affiliateinvitee = None

                                # Increment the subscriber count for the plan
                                plan = coin_subscription.plan
                                plan.subscriber_count = F("subscriber_count") + 1
                                plan.save()

                    elif result.get("status") == -1:
                        # Transaction failed, Delete the subscription object
                        coin_subscription.delete()
                    else:
                        logger.warning(
                            f"Transaction ID: {coin_subscription.subscription_id}, status: {result.get('status')}"
                        )
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
    now = timezone.now()
    expired_subscriptions = CoinSubscription.objects.filter(
        status=CoinSubscription.SubscriptionStatus.ACTIVE,
        expiration_date__lte=now,
    )

    for subscription in expired_subscriptions:
        subscription.status = CoinSubscription.SubscriptionStatus.EXPIRED
        subscription.save()

        # Send email to the subscriber
        subject = "Sub365.co: Your Coin Subscription has Expired"
        message = f"Dear {subscription.subscriber}, your coin subscription has expired. Thank you for using our services."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [subscription.subscriber.email]
        send_mail(subject, message, from_email, recipient_list)


@shared_task(name="check_coin_withdrawal_status")
def check_coin_withdrawal_status(affiliate_id, serverowner_id):
    try:
        affiliate = Affiliate.objects.filter(pk=affiliate_id).first()
        serverowner = ServerOwner.objects.get(id=serverowner_id)
        endpoint = "https://www.coinpayments.net/api.php"
        data = (
            f"version=1&cmd=create_withdrawal&amount={serverowner.total_coin_pending_commissions}&currency="
            + settings.COINBASE_CURRENCY
            + f"&add_tx_fee=1&auto_confirm=1&address={affiliate.paymentdetail.body}&key={serverowner.coinbase_api_public_key}&format=json"
        )
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "HMAC": create_hmac_signature(data, serverowner.coinbase_api_secret_key),
        }
        response = requests.post(endpoint, data=data, headers=header)
        result = response.json()["result"]
        if isinstance(result, dict):
            if result.get("status") == 1:
                # Affiliate payment was successful
                # Update the server owner's total_coin_pending_commissions
                serverowner.total_coin_pending_commissions = (
                    F("total_coin_pending_commissions")
                    - affiliate.pending_coin_commissions
                )
                serverowner.save()

                # Update the affiliate's pending_commissions and total_coin_commissions_paid fields
                affiliate.total_coin_commissions_paid = (
                    F("total_coin_commissions_paid")
                    + affiliate.pending_coin_commissions
                )
                affiliate.pending_coin_commissions = Decimal(0)
                affiliate.last_payment_date = timezone.now()
                affiliate.save()

                # Mark the associated AffiliatePayment instances as paid
                affiliate_payments = AffiliatePayment.objects.filter(
                    serverowner=serverowner, affiliate=affiliate, paid=False
                )
                affiliate_payments.update(
                    paid=True, date_payment_confirmed=timezone.now()
                )
            elif result.get("status") == 1:
                # TODO: Payment failed, send a mail to serverowner making an attempt
                pass
            else:
                logger.warning(f"Withdrawal status: {result.get('status')}")
        else:
            logger.warning(f"Unexpected format for 'result': {result}")
    except ObjectDoesNotExist:
        affiliate = None
        serverowner = None
    except requests.exceptions.RequestException as e:
        logger.exception(f"Coinbase API request failed: {e}")
    except (ValueError, KeyError) as e:
        logger.exception(f"Failed to parse Coinbase API response: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
