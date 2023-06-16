from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model with additional fields.
    """

    is_serverowner = models.BooleanField(default=False)
    is_subscriber = models.BooleanField(default=False)


class ServerOwner(models.Model):
    """
    Model for server owners.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    subdomain = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.username


class Server(models.Model):
    """
    Model for servers.
    """

    owner = models.ForeignKey(ServerOwner, on_delete=models.CASCADE, related_name='servers')
    server_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    choice_server = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Subscriber(models.Model):
    """
    Model for subscribers.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return self.username


class StripePlan(models.Model):
    """
    Model for Stripe plans.
    """

    user = models.ForeignKey(ServerOwner, on_delete=models.CASCADE, related_name='plans')
    product_id = models.CharField(max_length=100)
    price_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    description = models.TextField(max_length=300)
    currency = models.CharField(max_length=3)
    interval = models.CharField(max_length=10)
    subscriber_count = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """
    Model for subscriptions.
    """

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = 'A', _('Active')
        INACTIVE = 'I', _('Inactive')

    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='subscriptions')
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    plan = models.ForeignKey(StripePlan, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField(default=timezone.now)
    expiration_date = models.DateTimeField()
    subscription_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(
        max_length=1, choices=SubscriptionStatus.choices, default=SubscriptionStatus.INACTIVE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
        get_latest_by = ['-created']

    def __str__(self):
        return f'Subscription #{self.id}'

    def calculate_expiration_date(self):
        """
        Calculate the expiration date of the subscription.
        """
        #TODO Use stripe expiration date instead
        return self.subscription_date + timezone.timedelta(days=30)
