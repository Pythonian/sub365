from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import CoinSubscription


class Command(BaseCommand):
    help = "Mark expired subscriptions as Expired"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_subscriptions = CoinSubscription.objects.filter(
            expiration_date__lt=now, status=CoinSubscription.SubscriptionStatus.ACTIVE
        )
        expired_subscriptions.update(status=CoinSubscription.SubscriptionStatus.EXPIRED)
