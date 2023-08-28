from decimal import ROUND_DOWN, Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model with additional fields.
    """

    is_serverowner = models.BooleanField(default=False)
    is_subscriber = models.BooleanField(default=False)
    is_affiliate = models.BooleanField(default=False)


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
    affiliate_commission = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    total_pending_commissions = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total pending dollar commissions to be paid by the server owner",
    )
    total_coin_pending_commissions = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Total pending coin commissions to be paid by the server owner",
    )
    coinbase_api_secret_key = models.CharField(max_length=255, blank=True, null=True)
    coinbase_api_public_key = models.CharField(max_length=255, blank=True, null=True)
    coinbase_onboarding = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    def get_choice_server(self):
        """
        Retrieve the choice server marked as True for the ServerOwner.

        Returns:
            Server: The choice server of the ServerOwner marked as True.
        """
        return self.servers.filter(choice_server=True).first()

    # ===== SERVEROWNER PLAN METHODS ===== #

    def get_plans(self):
        """
        Retrieve the server owner's plans from the database.

        Returns:
            QuerySet: QuerySet of Plan objects belonging to the server owner.
        """
        if self.coinbase_onboarding:
            return self.coin_plans.all()
        else:
            return self.plans.all()

    def get_plan_count(self):
        """
        Get the total count of plans created by the server owner.

        Returns:
            int: The total count of plans created by the server owner.
        """
        if self.coinbase_onboarding:
            return self.coin_plans.count()
        else:
            return self.plans.count()

    def get_active_plans(self, limit=3):
        """
        Get the active plans created by the ServerOwner.

        Returns:
            Queryset: QuerySet of Plan objects set to a limit.
        """
        if self.coinbase_onboarding:
            return self.get_plans().filter(status=CoinPlan.PlanStatus.ACTIVE)[:limit]
        else:
            return self.get_plans().filter(status=StripePlan.PlanStatus.ACTIVE)[:limit]

    def get_active_plans_count(self):
        """
        Get the total number of active plans.

        Returns:
            int: The total number of active plans.
        """
        if self.coinbase_onboarding:
            return (
                self.get_plans().filter(status=CoinPlan.PlanStatus.ACTIVE.value).count()
            )
        else:
            return (
                self.get_plans()
                .filter(status=StripePlan.PlanStatus.ACTIVE.value)
                .count()
            )

    def get_inactive_plans_count(self):
        """
        Get the total number of inactive plans.

        Returns:
            int: The total number of inactive plans.
        """
        if self.coinbase_onboarding:
            return self.coin_plans.filter(
                status=CoinPlan.PlanStatus.INACTIVE.value
            ).count()
        else:
            return self.plans.filter(
                status=StripePlan.PlanStatus.INACTIVE.value
            ).count()

    def get_popular_plans(self, limit=3):
        """
        Get the popular plans created by the ServerOwner based on number of subscribers.

        Returns:
            QuerySet: QuerySet of Plan objects ordered by subscriber count
                      in descending order excluding plans with no subscribers.
        """
        if self.coinbase_onboarding:
            return self.coin_plans.filter(
                status=CoinPlan.PlanStatus.ACTIVE, subscriber_count__gt=0
            ).order_by("-subscriber_count")[:limit]
        else:
            return self.plans.filter(
                status=StripePlan.PlanStatus.ACTIVE, subscriber_count__gt=0
            ).order_by("-subscriber_count")[:limit]

    # ===== SERVEROWNER AFFILIATE METHODS ===== #

    def get_total_payments_to_affiliates(self):
        """
        Get the total payments the server owner has paid to affiliates.
        """
        if self.coinbase_onboarding:
            return (
                self.affiliate_set.aggregate(
                    total_coin_payments=Sum("total_coin_commissions_paid")
                ).get("total_coin_payments")
                or 0
            )
        else:
            return (
                self.affiliate_set.aggregate(
                    total_payments=Sum("total_commissions_paid")
                ).get("total_payments")
                or 0
            )

    def get_pending_affiliates(self):
        """
        Get a list of pending affiliates that the server owner is to pay.
        """
        if self.coinbase_onboarding:
            return self.affiliate_set.exclude(pending_coin_commissions=0)
        else:
            return self.affiliate_set.exclude(pending_commissions=0)

    def get_pending_affiliates_count(self):
        """
        Get the total number of affiliates who are yet to be paid by serverowner.
        """
        return self.get_pending_affiliates().count()

    def get_affiliates(self):
        """
        Get a list of all affiliates associated with the server owner.
        """
        return Affiliate.objects.filter(serverowner=self)

    def get_affiliate_payments(self):
        """
        Get the list of Affiliates payments associated with the Serverowner.
        """
        return AffiliatePayment.objects.filter(serverowner=self)

    def get_pending_affiliate_payments(self):
        """
        Get the pending commissions the server owner is to pay affiliates.
        """
        return self.get_affiliate_payments().filter(paid=False)

    def get_confirmed_affiliate_payments(self):
        """
        Get the confirmed payment of commissions the server owner has paid affiliates.
        """
        return self.get_affiliate_payments().filter(paid=True)

    def get_affiliates_confirmed_payment_count(self):
        """
        Get the total number of affiliates who have been paid by serverowner.
        """
        return self.get_confirmed_affiliate_payments().count()

    def get_confirmed_payment_amount(self):
        """
        Get the total amount of confirmed payments the server owner has paid affiliates.
        """
        confirmed_payments = self.get_confirmed_affiliate_payments()
        if self.coinbase_onboarding:
            total_amount = confirmed_payments.aggregate(total=Sum("coin_amount")).get("total")
            if total_amount is None:
                total_amount = 0
            return total_amount
        else:
            total_amount = confirmed_payments.aggregate(total=Sum("amount")).get("total")
            if total_amount is None:
                total_amount = 0
            return total_amount

    def calculate_affiliate_commission(self, subscription_amount):
        """
        Calculate the affiliate commission based on the subscription
        amount and affiliate commission percentage.
        """
        if self.coinbase_onboarding:
            commission_percentage = self.affiliate_commission
            if commission_percentage is None:
                return 0
            subscription_amount = float(subscription_amount)
            commission_amount = (subscription_amount * commission_percentage) / 100
        else:
            commission_percentage = self.affiliate_commission
            if commission_percentage is None:
                return 0

            commission_amount = (subscription_amount * commission_percentage) / 100

        return commission_amount

    def get_affiliate_users(self):
        """
        Retrieve the affiliates associated with the ServerOwner.

        Returns:
            QuerySet: QuerySet of Affiliate objects associated with the ServerOwner.
        """
        affiliates = Affiliate.objects.filter(serverowner=self)
        affiliate_counts = []

        for affiliate in affiliates:
            invite_count = AffiliateInvitee.objects.filter(affiliate=affiliate).count()
            affiliate_counts.append((affiliate, invite_count))

        return affiliate_counts

    def get_total_affiliates(self):
        """
        Get the total number of affiliates associated with the ServerOwner.

        Returns:
            int: The total number of affiliates.
        """
        return self.get_affiliates().count()

    # ===== SERVEROWNER SUBSCRIBER METHODS ===== #

    def get_subscribed_users(self):
        """
        Retrieve the subscribers who subscribed to any of the plans created by the
        ServerOwner.

        Returns:
            QuerySet: QuerySet of Subscriber objects who subscribed via the ServerOwner.
        """
        return Subscriber.objects.filter(subscribed_via=self)

    def get_total_subscribers(self):
        """
        Get the total number of subscribers who subscribed via the ServerOwner.

        Returns:
            int: The total number of subscribers.
        """
        return self.get_subscribed_users().count()

    # ===== SERVEROWNER SUBSCRIPTION METHODS ===== #

    def get_latest_subscriptions(self, limit=3):
        """
        Retrieve the latest subscriptions for the ServerOwner.

        Args:
            limit (int): The maximum number of subscriptions to retrieve. Default is 3.

        Returns:
            QuerySet: QuerySet of Subscription objects ordered by creation date.
        """
        if self.coinbase_onboarding:
            return CoinSubscription.objects.filter(
                subscribed_via=self, status=CoinSubscription.SubscriptionStatus.ACTIVE
            )[:limit]
        else:
            return Subscription.objects.filter(
                subscribed_via=self, status=Subscription.SubscriptionStatus.ACTIVE
            )[:limit]

    def get_total_earnings(self):
        """
        Calculate the total earnings of the ServerOwner based on subscriptions with
        statuses ACTIVE, EXPIRED, and CANCELED.

        Returns:
            Decimal: The total earnings amount formatted with two decimal places.
        """
        if self.coinbase_onboarding:
            total_earnings = (
                CoinSubscription.objects.filter(
                    subscribed_via=self,
                    status__in=[
                        CoinSubscription.SubscriptionStatus.ACTIVE,
                        CoinSubscription.SubscriptionStatus.EXPIRED,
                        CoinSubscription.SubscriptionStatus.CANCELED,
                    ],
                )
                .aggregate(total=Sum("plan__amount"))
                .get("total")
            )
        else:
            total_earnings = (
                Subscription.objects.filter(
                    subscribed_via=self,
                    status__in=[
                        Subscription.SubscriptionStatus.ACTIVE,
                        Subscription.SubscriptionStatus.EXPIRED,
                        Subscription.SubscriptionStatus.CANCELED,
                    ],
                )
                .aggregate(total=Sum("plan__amount"))
                .get("total")
            )

        if total_earnings is not None:
            total_earnings = Decimal(total_earnings)
        else:
            total_earnings = Decimal(0)

        return total_earnings.quantize(Decimal("0.00"), rounding=ROUND_DOWN)

    def get_active_subscribers_count(self):
        """
        Get the total number of subscribers with active subscriptions.

        Returns:
            int: The total number of subscribers with active subscriptions.
        """
        if self.coinbase_onboarding:
            return (
                self.get_subscribed_users()
                .filter(
                    coin_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE
                )
                .count()
            )
        else:
            return (
                self.get_subscribed_users()
                .filter(subscriptions__status=Subscription.SubscriptionStatus.ACTIVE)
                .count()
            )

    def get_inactive_subscribers_count(self):
        """
        Get the total number of subscribers with inactive subscriptions.

        Returns:
            int: The total number of subscribers with inactive subscriptions.
        """
        if self.coinbase_onboarding:
            return (
                self.get_subscribed_users()
                .exclude(
                    coin_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE
                )
                .count()
            )
        else:
            return (
                self.get_subscribed_users()
                .exclude(subscriptions__status=Subscription.SubscriptionStatus.ACTIVE)
                .count()
            )


class Server(models.Model):
    """
    Model for servers.
    """

    owner = models.ForeignKey(
        ServerOwner, on_delete=models.CASCADE, related_name="servers"
    )
    server_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=255, blank=True, null=True)
    choice_server = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

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
    subscribed_via = models.ForeignKey(
        ServerOwner, on_delete=models.SET_NULL, blank=True, null=True
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.username

    def has_active_subscription(self):
        if self.subscribed_via.coinbase_onboarding:
            return self.coin_subscriptions.filter(
                status=CoinSubscription.SubscriptionStatus.ACTIVE,
                expiration_date__gt=timezone.now(),
            ).exists()
        else:
            return self.subscriptions.filter(
                status=Subscription.SubscriptionStatus.ACTIVE,
                expiration_date__gt=timezone.now(),
            ).exists()

    def get_subscriptions(self):
        if self.subscribed_via.coinbase_onboarding:
            return self.coin_subscriptions.all()
        else:
            return self.subscriptions.all()


class Affiliate(models.Model):
    subscriber = models.OneToOneField(Subscriber, on_delete=models.CASCADE)
    affiliate_link = models.CharField(
        max_length=255, unique=True, blank=True, null=True
    )
    discord_id = models.CharField(
        max_length=255, primary_key=True, help_text="Discord ID of the Affiliate"
    )
    server_id = models.CharField(max_length=255)
    serverowner = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    total_commissions_paid = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total commissions paid to the affiliate",
    )
    total_coin_commissions_paid = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Total coin commissions paid to the affiliate",
    )
    pending_commissions = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    pending_coin_commissions = models.DecimalField(
        max_digits=20, decimal_places=8, default=0
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.subscriber.username

    def update_last_payment_date(self):
        self.last_payment_date = timezone.now()
        self.save()

    def get_total_invitation_count(self):
        """
        Get the total count of affiliate invitees.
        """
        return self.affiliateinvitee_set.all().count()

    def get_active_subscription_count(self):
        """
        Get the count of invitees with active subscriptions.
        """
        if self.serverowner.coinbase_onboarding:
            invitees_with_active_coin_subscriptions = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    coin_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE
                ).values("discord_id")
            )
            return invitees_with_active_coin_subscriptions.count()
        else:
            invitees_with_active_subscriptions = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    subscriptions__status=Subscription.SubscriptionStatus.ACTIVE
                ).values("discord_id")
            )
            return invitees_with_active_subscriptions.count()

    def calculate_conversion_rate(self):
        """
        Calculate the conversion rate of the affiliate.
        """
        invitees_count = self.affiliateinvitee_set.count()
        if self.serverowner.coinbase_onboarding:
            successful_invitees_count = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    Q(
                        coin_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE
                    )
                    | Q(
                        coin_subscriptions__status=CoinSubscription.SubscriptionStatus.CANCELED
                    )
                    | Q(
                        coin_subscriptions__status=CoinSubscription.SubscriptionStatus.EXPIRED
                    )
                ).values("discord_id")
            ).count()
        else:
            successful_invitees_count = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    Q(subscriptions__status=Subscription.SubscriptionStatus.ACTIVE)
                    | Q(subscriptions__status=Subscription.SubscriptionStatus.CANCELED)
                    | Q(subscriptions__status=Subscription.SubscriptionStatus.EXPIRED)
                ).values("discord_id")
            ).count()

        if invitees_count > 0:
            conversion_rate = (successful_invitees_count / invitees_count) * 100
        else:
            conversion_rate = 0

        return round(conversion_rate, 2)

    def get_affiliate_payments(self):
        """
        Get the affiliate payments associated with this affiliate.
        """
        return AffiliatePayment.objects.filter(affiliate=self)

    def get_affiliate_invitees(self):
        """
        Get a list of all affiliate invitees associated with this affiliate.
        """
        return self.affiliateinvitee_set.all()


class AffiliateInvitee(models.Model):
    """Model table for an Invited user by an Affiliate"""

    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE)
    invitee_discord_id = models.CharField(
        max_length=255, unique=True, help_text="Discord ID of the Invitee"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.invitee_discord_id

    def get_affiliateinvitee_name(self):
        """
        Get the username of the Invitee
        """
        subscriber = Subscriber.objects.filter(
            discord_id=self.invitee_discord_id
        ).first()
        if subscriber:
            return subscriber.username
        return None

    def get_affiliate_commission_payment(self):
        subscriber = Subscriber.objects.filter(
            discord_id=self.invitee_discord_id
        ).first()
        if subscriber:
            if self.affiliate.serverowner.coinbase_onboarding:
                subscription = subscriber.coin_subscriptions.order_by(
                    "-created"
                ).first()
                if subscription:
                    subscription_amount = subscription.coin_amount
                    server_owner = self.affiliate.serverowner
                    commission_payment = server_owner.calculate_affiliate_commission(
                        subscription_amount
                    )
                    return commission_payment
            else:
                subscription = subscriber.subscriptions.order_by("-created").first()
                if subscription:
                    subscription_amount = subscription.plan.amount
                    server_owner = self.affiliate.serverowner
                    commission_payment = server_owner.calculate_affiliate_commission(
                        subscription_amount
                    )
                    return commission_payment
        return 0

    def calculate_affiliate_payment_commission(self):
        """
        Calculate the total affiliate payment commission received for this AffiliateInvitee.
        """
        affiliate_payments = AffiliatePayment.objects.filter(
            affiliate=self.affiliate,
            subscriber__discord_id=self.invitee_discord_id,
            paid=True,
        )
        if self.affiliate.serverowner.coinbase_onboarding:
            total_commission = affiliate_payments.aggregate(
                total_commission=Sum("coin_amount")
            ).get("total_commission")
            return total_commission or 0
        else:
            total_commission = affiliate_payments.aggregate(
                total_commission=Sum("amount")
            ).get("total_commission")
            return total_commission or 0


class AffiliatePayment(models.Model):
    serverowner = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    affiliate = models.ForeignKey(
        Affiliate, on_delete=models.CASCADE, help_text="Discord ID of the Affiliate"
    )
    subscriber = models.ForeignKey(
        Subscriber,
        on_delete=models.CASCADE,
        help_text="The Affiliate Invitee who subscribed",
    )
    amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text="The dollar commission to be paid.",
    )
    coin_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
        help_text="The coin commission to be paid.",
    )
    paid = models.BooleanField(default=False)
    date_payment_confirmed = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Affiliate Payment #{self.id}"


class StripePlan(models.Model):
    """
    Model for Stripe plans.
    """

    class PlanStatus(models.TextChoices):
        ACTIVE = "A", "Active"
        INACTIVE = "I", "Inactive"

    user = models.ForeignKey(
        ServerOwner, on_delete=models.CASCADE, related_name="plans"
    )
    product_id = models.CharField(max_length=100)
    price_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    description = models.TextField(max_length=300, help_text="300 characters")
    currency = models.CharField(max_length=3, default="usd")
    interval_count = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    subscriber_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=1, choices=PlanStatus.choices, default=PlanStatus.ACTIVE
    )
    discord_role_id = models.CharField(
        max_length=255, help_text="ID of Discord role to be assigned to subscribers"
    )
    permission_description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Description of permissions to be given to subscribers",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name

    def total_earnings(self):
        # Calculate the total earnings for this plan
        subscribers = Subscription.objects.filter(plan=self, subscribed_via=self.user)
        total_earnings = subscribers.aggregate(total=models.Sum("plan__amount"))[
            "total"
        ]
        return total_earnings or Decimal(0)

    def get_stripeplan_subscribers(self):
        # Get all subscribers for this plan, filtered by the server owner
        return Subscription.objects.filter(plan=self, subscribed_via=self.user)

    def active_subscriptions_count(self):
        # Count the number of active subscriptions for this plan
        subscribers = self.get_stripeplan_subscribers()
        active_subscriptions = subscribers.filter(
            status=Subscription.SubscriptionStatus.ACTIVE
        )
        return active_subscriptions.count()

    def total_subscriptions_count(self):
        # Count the total number of subscriptions for this plan
        subscribers = self.get_stripeplan_subscribers()
        return subscribers.count()


class CoinPlan(models.Model):
    """
    Model for Coin plans.
    """

    class PlanStatus(models.TextChoices):
        ACTIVE = "A", "Active"
        INACTIVE = "I", "Inactive"

    serverowner = models.ForeignKey(
        ServerOwner, on_delete=models.CASCADE, related_name="coin_plans"
    )
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    interval_count = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    description = models.TextField(max_length=300, help_text="300 characters")
    status = models.CharField(
        max_length=1, choices=PlanStatus.choices, default=PlanStatus.ACTIVE
    )
    subscriber_count = models.IntegerField(default=0)
    discord_role_id = models.CharField(
        max_length=255, help_text="ID of Discord role to be assigned to subscribers"
    )
    permission_description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Description of permissions to be given to subscribers",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name

    def total_earnings(self):
        # Calculate the total earnings for this plan
        subscribers = CoinSubscription.objects.filter(
            plan=self, subscribed_via=self.serverowner
        )
        total_earnings = subscribers.aggregate(total=models.Sum("plan__amount"))[
            "total"
        ]
        return total_earnings or Decimal(0)

    def get_coinplan_subscribers(self):
        # Get all subscribers for this plan, filtered by the server owner
        return CoinSubscription.objects.filter(
            plan=self, subscribed_via=self.serverowner
        )

    def active_subscriptions_count(self):
        # Count the number of active subscriptions for this plan
        subscribers = self.get_coinplan_subscribers()
        active_subscriptions = subscribers.filter(
            status=CoinSubscription.SubscriptionStatus.ACTIVE
        )
        return active_subscriptions.count()

    def total_subscriptions_count(self):
        # Count the total number of subscriptions for this plan
        subscribers = self.get_coinplan_subscribers()
        return subscribers.count()


class Subscription(models.Model):
    """
    Model for subscriptions.
    """

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "A", "Active"
        INACTIVE = "I", "Inactive"
        EXPIRED = "E", "Expired"
        CANCELED = "C", "Canceled"

    subscriber = models.ForeignKey(
        Subscriber, on_delete=models.CASCADE, related_name="subscriptions"
    )
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    plan = models.ForeignKey(StripePlan, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)
    subscription_id = models.CharField(max_length=200, blank=True, null=True)
    session_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(
        max_length=1,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INACTIVE,
    )
    value = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]
        get_latest_by = ["-created"]

    def __str__(self):
        return f"Subscription #{self.id}"


class CoinSubscription(models.Model):
    """
    Model for coin subscriptions.
    """

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "A", "Active"
        PENDING = "P", "Pending"
        EXPIRED = "E", "Expired"
        CANCELED = "C", "Canceled"

    subscriber = models.ForeignKey(
        Subscriber, on_delete=models.CASCADE, related_name="coin_subscriptions"
    )
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    plan = models.ForeignKey(CoinPlan, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField(blank=True, null=True)
    expiration_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=1,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
    )
    coin_amount = models.CharField(max_length=225, blank=True, null=True)
    subscription_id = models.CharField(max_length=225, blank=True, null=True)
    address = models.CharField(max_length=225, blank=True, null=True)
    checkout_url = models.CharField(max_length=225, blank=True, null=True)
    status_url = models.CharField(max_length=225, blank=True, null=True)
    qrcode_url = models.CharField(max_length=225, blank=True, null=True)
    value = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]
        get_latest_by = ["-created"]

    def __str__(self):
        return f"Coin Subscription #{self.id}"


class PaymentDetail(models.Model):
    affiliate = models.OneToOneField(Affiliate, on_delete=models.CASCADE)
    litecoin_address = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment detail for {self.affiliate}"


class AccessCode(models.Model):
    code = models.CharField(max_length=5, unique=True)
    used_by = models.ForeignKey(
        ServerOwner, on_delete=models.SET_NULL, blank=True, null=True
    )
    is_used = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
