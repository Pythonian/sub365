import logging
import requests

from celery import shared_task
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from .models import AffiliateInvitee, AffiliatePayment, CoinSubscription
from .utils import create_hmac_signature

logger = logging.getLogger(__name__)


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
            # if result and result.get('status') == 1:
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
    except requests.exceptions.RequestException as e:
        logger.exception(f"Coinbase API request failed: {e}")
    except (ValueError, KeyError) as e:
        logger.exception(f"Failed to parse Coinbase API response: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


# @shared_task(name='check_coin_transaction_status')
# def check_coin_transaction_status(txn_id, api_secret_key, api_public_key, subscriber_id, plan_id):

#     try:
#         endpoint = "https://www.coinpayments.net/api.php"
#         data = f"version=1&cmd=get_tx_info&txid={txn_id}&key={api_public_key}&format=json"
#         header = {
#             "Content-Type": "application/x-www-form-urlencoded",
#             "HMAC": create_hmac_signature(data, api_secret_key),
#         }
#         response = requests.post(endpoint, data=data, headers=header)
#         result = response.json()['result']
#         logger.info(f"Response from API: {result}")
#         if isinstance(result, dict):
#             # if result and result.get('status') == 1:
#             if result.get('status') == 1:
#                 # Transaction was successful, create CoinSubscription for the Subscriber
#                 subscriber = Subscriber.objects.get(pk=subscriber_id)
#                 plan = CoinPlan.objects.get(pk=plan_id)

#                 CoinSubscription.objects.create(
#                     subscriber=subscriber,
#                     subscribed_via=subscriber.subscribed_via,
#                     plan=plan,
#                     subscription_date=timezone.now(),
#                     expiration_date=timezone.now() + timedelta(days=30),
#                     status=CoinSubscription.SubscriptionStatus.ACTIVE,
#                     value=1,
#                 )
#                 try:
#                     affiliateinvitee = AffiliateInvitee.objects.get(
#                         invitee_discord_id=subscriber.discord_id
#                     )
#                     affiliatepayment = AffiliatePayment.objects.create(  # noqa
#                         serverowner=subscriber.subscribed_via,
#                         affiliate=affiliateinvitee.affiliate,
#                         subscriber=subscriber,
#                         amount=affiliateinvitee.get_affiliate_commission_payment(),
#                     )

#                     affiliateinvitee.affiliate.update_last_payment_date()
#                     affiliateinvitee.affiliate.pending_commissions = (
#                         F("pending_commissions")
#                         + affiliateinvitee.get_affiliate_commission_payment()
#                     )
#                     affiliateinvitee.affiliate.save()

#                     subscriber.subscribed_via.total_pending_commissions = (
#                         F("total_pending_commissions")
#                         + affiliateinvitee.get_affiliate_commission_payment()
#                     )
#                     subscriber.subscribed_via.save()

#                 except ObjectDoesNotExist:
#                     affiliateinvitee = None

#                 # Increment the subscriber count for the plan
#                 plan.subscriber_count = F("subscriber_count") + 1
#                 plan.save()

#             else:
#                 logger.warning(
#                     f"Transaction status check failed for txn_id: {txn_id}, status: {result.get('status')}")
#         else:
#             logger.warning(f"Unexpected format for 'result': {result}")
#     except requests.exceptions.RequestException as e:
#         logger.exception(f"Coinbase API request failed: {e}")
#     except (ValueError, KeyError) as e:
#         logger.exception(f"Failed to parse Coinbase API response: {e}")
#     except Exception as e:
#         logger.exception(f"An unexpected error occurred: {e}")
