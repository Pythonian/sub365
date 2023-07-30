import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.utils import timezone

import requests
from celery import shared_task

from .models import (
    Affiliate,
    AffiliateInvitee,
    AffiliatePayment,
    CoinSubscription,
    ServerOwner,
)
from .utils import create_hmac_signature

logger = logging.getLogger(__name__)


@shared_task(name="check_coin_withdrawal_status")
def check_coin_withdrawal_status(affiliate_id, serverowner_id):
    try:
        affiliate = Affiliate.objects.filter(pk=affiliate_id).first()
        serverowner = ServerOwner.objects.get(id=serverowner_id)
        endpoint = "https://www.coinpayments.net/api.php"
        data = (
            f"version=1&cmd=create_withdrawal&amount={serverowner.total_pending_btc_commissions}&currency="
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
                # Update the server owner's total_pending_commissions
                serverowner.total_pending_commissions = (
                    F("total_pending_commissions") - affiliate.pending_commissions
                )
                serverowner.save()

                # Update the affiliate's pending_commissions and total_commissions_paid fields
                affiliate.total_commissions_paid = (
                    F("total_commissions_paid") + affiliate.pending_commissions
                )
                affiliate.pending_commissions = Decimal(0)
                affiliate.last_payment_date = timezone.now()
                affiliate.save()

                # Mark the associated AffiliatePayment instances as paid
                affiliate_payments = AffiliatePayment.objects.filter(
                    serverowner=serverowner, affiliate=affiliate, paid=False
                )
                affiliate_payments.update(
                    paid=True, date_payment_confirmed=timezone.now()
                )
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


@shared_task(name="check_coin_transaction_status")
def check_coin_transaction_status(pk):
    try:
        coin_subscription = CoinSubscription.objects.get(pk=pk)
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
        logger.info(f"Response from API: {result}")
        if isinstance(result, dict):
            if result.get("status") == 1:
                # Transaction was successful
                coin_subscription.status = CoinSubscription.SubscriptionStatus.ACTIVE
                coin_subscription.subscription_date = timezone.now()
                coin_subscription.expiration_date = timezone.now() + timedelta(days=30)

                subscriber = coin_subscription.subscriber

                try:
                    affiliateinvitee = AffiliateInvitee.objects.get(
                        invitee_discord_id=subscriber.discord_id
                    )
                    affiliatepayment = AffiliatePayment.objects.create(  # noqa
                        serverowner=subscriber.subscribed_via,
                        affiliate=affiliateinvitee.affiliate,
                        subscriber=subscriber,
                        amount=affiliateinvitee.get_affiliate_commission_payment(),
                    )

                    affiliateinvitee.affiliate.update_last_payment_date()
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

                except AffiliateInvitee.DoesNotExist:
                    affiliateinvitee = None

                # Increment the subscriber count for the plan
                plan = coin_subscription.plan
                plan.subscriber_count = F("subscriber_count") + 1
                plan.save()

            else:
                logger.warning(
                    f"Transaction status: {coin_subscription.subscription_id}, status: {result.get('status')}"
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
