import logging
import requests

from celery import shared_task
from datetime import timedelta
from django.utils import timezone

from config.celery import app

from .models import CoinSubscription, Subscriber, ServerOwner, CoinPlan
from .utils import create_hmac_signature

logger = logging.getLogger(__name__)


@shared_task
def check_coin_transaction_status(*args, **kwargs):
    txn_id = kwargs["txn_id"]
    api_secret_key = kwargs["api_secret_key"]
    api_public_key = kwargs["api_public_key"]
    subscriber_id = kwargs["subscriber_id"]
    subscribed_via_id = kwargs["subscribed_via_id"]
    plan_id = kwargs["plan_id"]

    try:
        endpoint = "https://www.coinpayments.net/api.php"
        data = f"version=1&cmd=get_tx_info&txid={txn_id}&key={api_public_key}&format=json"
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "HMAC": create_hmac_signature(data, api_secret_key),
        }
        response = requests.post(endpoint, data=data, headers=header)
        result = response.json()['result']
        if result and result.get('status') == 1:
            # Transaction was successful, create CoinSubscription for the Subscriber
            subscriber = Subscriber.objects.get(pk=subscriber_id)
            subscribed_via = ServerOwner.objects.get(pk=subscribed_via_id)
            plan = CoinPlan.objects.get(pk=plan_id)

            CoinSubscription.objects.create(
                subscriber=subscriber,
                subscribed_via=subscribed_via,
                plan=plan,
                subscription_date=timezone.now(),
                expiration_date=timezone.now() + timedelta(days=30),
                status=CoinSubscription.SubscriptionStatus.ACTIVE,
                value=1,
            )
        else:
            logger.warning(
                f"Transaction status check failed for txn_id: {txn_id}, status: {result.get('status')}")
    except requests.exceptions.RequestException as e:
        logger.exception(f"Coinbase API request failed: {e}")
    except (ValueError, KeyError) as e:
        logger.exception(f"Failed to parse Coinbase API response: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


app.conf.beat_schedule = {
    'check_coin_transaction_status_every_30_seconds': {
        'task': 'accounts.tasks.check_coin_transaction_status',
        'schedule': timedelta(seconds=30),
    },
}
