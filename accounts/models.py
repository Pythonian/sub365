from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from decimal import Decimal, ROUND_DOWN
from django.core.validators import MinValueValidator, MaxValueValidator


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
    subdomain = models.CharField(max_length=20)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.username

    def get_choice_server(self):
        """
        Retrieve the choice server marked as True for the ServerOwner.

        Returns:
            Server: The choice server of the ServerOwner marked as True.
        """
        return self.servers.filter(choice_server=True).first()

    def get_stripe_plans(self):
        """
        Retrieve the server owner's Stripe plans from the database.

        Returns:
            QuerySet: QuerySet of StripePlan objects belonging to the server owner.
        """
        return self.plans.all()

    def get_plan_count(self):
        """
        Get the total count of plans created by the server owner.

        Returns:
            int: The total count of plans created by the server owner.
        """
        return self.plans.count()

    def get_popular_plans(self, limit=3):
        """
        Get the popular plans created by the ServerOwner based on number of subscribers.

        Returns:
            QuerySet: QuerySet of StripePlan objects ordered by subscriber count in descending order.
        """
        return self.plans.filter(status=StripePlan.PlanStatus.ACTIVE).order_by('-subscriber_count')[:limit]

    def get_subscribed_users(self):
        """
        Retrieve the subscribers who subscribed to any of the plans created by the ServerOwner.

        Returns:
            QuerySet: QuerySet of Subscriber objects who subscribed via the ServerOwner.
        """
        return Subscriber.objects.filter(subscribed_via=self)

    def get_latest_subscriptions(self, limit=3):
        """
        Retrieve the latest subscriptions for the ServerOwner.

        Args:
            limit (int): The maximum number of subscriptions to retrieve. Default is 3.

        Returns:
            QuerySet: QuerySet of Subscription objects ordered by creation date (latest first).
        """
        return Subscription.objects.filter(subscribed_via=self, status=Subscription.SubscriptionStatus.ACTIVE)[:limit]

    def get_total_subscriptions(self):
        """
        Get the total number of subscriptions created for the ServerOwner.

        Returns:
            int: The total number of subscriptions.
        """
        return Subscription.objects.filter(subscribed_via=self).count()

    def get_total_subscribers(self):
        """
        Get the total number of subscribers who subscribed via the ServerOwner.

        Returns:
            int: The total number of subscribers.
        """
        return self.get_subscribed_users().count()

    def get_total_earnings(self):
        """
        Calculate the total earnings of the ServerOwner based on subscriptions.

        Returns:
            Decimal: The total earnings amount formatted with two decimal places.
        """
        total_earnings = Subscription.objects.filter(subscribed_via=self).aggregate(total=Sum('plan__amount')).get('total')
        if total_earnings is not None:
            total_earnings = Decimal(total_earnings).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        else:
            total_earnings = Decimal(0)
        return total_earnings


class Server(models.Model):
    """
    Model for servers.
    """

    owner = models.ForeignKey(ServerOwner, on_delete=models.CASCADE, related_name='servers')
    server_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=255, blank=True, null=True)
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
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.username

    def has_active_subscription(self):
        return self.subscriptions.filter(status=Subscription.SubscriptionStatus.ACTIVE, expiration_date__gt=timezone.now()).exists()

    def get_subscriptions(self):
        return self.subscriptions.all()


class StripePlan(models.Model):
    """
    Model for Stripe plans.
    """

    class PlanStatus(models.TextChoices):
        ACTIVE = 'A', 'Active'
        INACTIVE = 'I', 'Inactive'

    user = models.ForeignKey(ServerOwner, on_delete=models.CASCADE, related_name='plans')
    product_id = models.CharField(max_length=100)
    price_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    description = models.TextField(max_length=300, help_text='300 characters')
    currency = models.CharField(max_length=3, default='usd')
    interval_count = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    subscriber_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=1, choices=PlanStatus.choices, default=PlanStatus.ACTIVE)
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
        ACTIVE = 'A', 'Active'
        INACTIVE = 'I', 'Inactive'

    # class SubscriptionStatus(models.TextChoices):
    #     INCOMPLETE = 'I', 'Incomplete'
    #     TRIALING = 'T', 'Trialing'
    #     ACTIVE = 'A', 'Active'
    #     PAST_DUE = 'P', 'Past Due'
    #     CANCELED = 'C', 'Canceled'
    #     UNPAID = 'U', 'Unpaid'

    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='subscriptions')
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    plan = models.ForeignKey(StripePlan, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField()
    expiration_date = models.DateTimeField(blank=True, null=True)
    subscription_id = models.CharField(max_length=200, blank=True, null=True)
    session_id = models.CharField(max_length=200, blank=True, null=True)
    customer_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(
        max_length=1, choices=SubscriptionStatus.choices, default=SubscriptionStatus.INACTIVE)
    value = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1)])
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
        get_latest_by = ['-created']

    def __str__(self):
        return f'Subscription #{self.id}'
