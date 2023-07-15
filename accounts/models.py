from decimal import ROUND_DOWN, Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum, Q
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
        help_text="Total pending commissions to be paid by the server owner",
    )

    def get_total_payments_to_affiliates(self):
        """
        Get the total payments the server owner has paid to affiliates.
        """
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
        return self.affiliate_set.exclude(pending_commissions=0)

    def get_pending_affiliates_count(self):
        return self.get_pending_affiliates().count()

    def get_affiliates(self):
        """
        Get a list of all affiliates associated with the server owner.
        """
        return Affiliate.objects.filter(serverowner=self)

    def calculate_total_commissions(self):
        """
        Calculate the total commission the server owner is to pay.
        """
        affiliates = self.affiliate_set.all()
        total_commissions = 0
        for affiliate in affiliates:
            total_commissions += affiliate.get_pending_commissions()
        return total_commissions

    def update_pending_commissions(self, amount):
        """
        Update the total pending commissions of the server owner.
        """
        self.total_pending_commissions -= amount
        self.save()

    def update_total_pending_commissions(self):
        pending_payments = self.get_pending_affiliate_payments()
        total_pending_commissions = pending_payments.aggregate(total=Sum("amount")).get(
            "total"
        )
        if total_pending_commissions is None:
            total_pending_commissions = 0
        self.total_pending_commissions = total_pending_commissions
        self.save()

    def __str__(self):
        return self.username

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

    def get_affiliates_awaiting_payment(self):
        """
        Get the total number of affiliates who are yet to be paid by serverowner.
        """
        return self.get_pending_affiliate_payments().count()

    def get_pending_payment_amount(self):
        """
        Get the total amount of pending payments the server owner is to pay affiliates.
        """
        pending_payments = self.get_pending_affiliate_payments()
        total_amount = pending_payments.aggregate(total=Sum("amount")).get("total")
        if total_amount is None:
            total_amount = 0
        return total_amount

    def get_confirmed_affiliate_payments(self):
        """
        Get the confirmed payment of commissions the server owner has paid affiliates.
        """
        return self.get_affiliate_payments().filter(paid=True)

    def get_affiliates_confirmed_payment(self):
        """
        Get the total number of affiliates who have been paid by serverowner.
        """
        return self.get_confirmed_affiliate_payments().count()

    def get_confirmed_payment_amount(self):
        """
        Get the total amount of confirmed payments the server owner is to pay affiliates.
        """
        confirmed_payments = self.get_confirmed_affiliate_payments()
        total_amount = confirmed_payments.aggregate(total=Sum("amount")).get("total")
        if total_amount is None:
            total_amount = 0
        return total_amount

    def calculate_affiliate_commission(self, subscription_amount):
        """
        Calculate the affiliate commission based on the subscription
        amount and affiliate commission percentage.
        """
        commission_percentage = self.affiliate_commission
        if commission_percentage is None:
            return 0

        commission_amount = (subscription_amount * commission_percentage) / 100
        return commission_amount

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
            QuerySet: QuerySet of StripePlan objects ordered by subscriber count
                      in descending order excluding plans with no subscribers.
        """
        return self.plans.filter(
            status=StripePlan.PlanStatus.ACTIVE, subscriber_count__gt=0
        ).order_by("-subscriber_count")[:limit]

    def get_subscribed_users(self):
        """
        Retrieve the subscribers who subscribed to any of the plans created by the
        ServerOwner.

        Returns:
            QuerySet: QuerySet of Subscriber objects who subscribed via the ServerOwner.
        """
        return Subscriber.objects.filter(subscribed_via=self)

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

    def get_latest_subscriptions(self, limit=3):
        """
        Retrieve the latest subscriptions for the ServerOwner.

        Args:
            limit (int): The maximum number of subscriptions to retrieve. Default is 3.

        Returns:
            QuerySet: QuerySet of Subscription objects ordered by creation date.
        """
        return Subscription.objects.filter(
            subscribed_via=self, status=Subscription.SubscriptionStatus.ACTIVE
        )[:limit]

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
        total_earnings = (
            Subscription.objects.filter(subscribed_via=self)
            .aggregate(total=Sum("plan__amount"))
            .get("total")
        )
        if total_earnings is not None:
            total_earnings = Decimal(total_earnings).quantize(
                Decimal("0.00"), rounding=ROUND_DOWN
            )
        else:
            total_earnings = Decimal(0)
        return total_earnings

    def affiliate_commissions(self):
        """
        Calculate the sum of all commissions received by the serverowner from affiliates.
        """
        total_commissions = 0
        affiliates = self.affiliate_set.all()
        for affiliate in affiliates:
            total_commissions += affiliate.calculate_total_commissions()

        return total_commissions

    def get_active_subscribers_count(self):
        """
        Get the total number of subscribers with active subscriptions.

        Returns:
            int: The total number of subscribers with active subscriptions.
        """
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
        return (
            self.get_subscribed_users()
            .exclude(subscriptions__status=Subscription.SubscriptionStatus.ACTIVE)
            .count()
        )

    def get_active_plans_count(self):
        """
        Get the total number of active plans.

        Returns:
            int: The total number of active plans.
        """
        return self.plans.filter(status=StripePlan.PlanStatus.ACTIVE.value).count()

    def get_inactive_plans_count(self):
        """
        Get the total number of inactive plans.

        Returns:
            int: The total number of inactive plans.
        """
        return self.plans.filter(status=StripePlan.PlanStatus.INACTIVE.value).count()


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
    stripe_account_id = models.CharField(
        max_length=100, blank=True, null=True
    )  # TODO redundant
    subscribed_via = models.ForeignKey(
        ServerOwner, on_delete=models.SET_NULL, blank=True, null=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.username

    def has_active_subscription(self):
        return self.subscriptions.filter(
            status=Subscription.SubscriptionStatus.ACTIVE,
            expiration_date__gt=timezone.now(),
        ).exists()

    def get_subscriptions(self):
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
    pending_commissions = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def calculate_commission(self):
        """
        Calculate the commission for the affiliate since their last payment.
        """
        last_payment_date = self.last_payment_date
        if last_payment_date:
            affiliate_payments = self.affiliatepayment_set.filter(
                created__gt=last_payment_date, paid=True
            )
        else:
            affiliate_payments = self.affiliatepayment_set.filter(paid=True)

        commission = affiliate_payments.aggregate(total=Sum("amount")).get("total")
        return commission or 0

    def update_commissions_paid(self, amount):
        """
        Update the total commissions paid to the affiliate.
        """
        self.total_commissions_paid += amount
        self.save()

    def get_pending_commissions(self):
        """
        Get the total commissions pending for the affiliate.
        """
        commissions_paid = self.total_commissions_paid
        commissions_earned = self.calculate_commission()
        return commissions_earned - commissions_paid

    def update_last_payment_date(self):
        self.last_payment_date = timezone.now()
        self.save()

    def update_total_commissions_paid(self, amount):
        self.total_commissions_paid += amount
        self.save()

    def update_pending_commissions(self):
        commissions_paid = self.total_commissions_paid
        commissions_earned = self.calculate_commission()
        self.pending_commissions = commissions_earned - commissions_paid
        self.save()

    def __str__(self):
        return self.subscriber.username

    def get_affiliate_invitees(self):
        """
        Get the affiliate invitees associated with this affiliate along with their subscription status.
        """
        invitees = self.affiliateinvitee_set.all()
        invitees_with_status = []

        for invitee in invitees:
            subscriber = Subscriber.objects.filter(
                discord_id=invitee.invitee_discord_id
            ).first()
            if subscriber:
                subscription = subscriber.subscriptions.order_by("-created").first()
                if subscription:
                    status = subscription.status
                else:
                    status = Subscription.SubscriptionStatus.INACTIVE
                invitees_with_status.append({"invitee": invitee, "status": status})

        return invitees_with_status

    def get_total_invitation_count(self):
        """
        Get the total count of affiliate invitees.
        """
        return self.affiliateinvitee_set.all().count()

    def get_active_subscription_count(self):
        """
        Get the count of invitees with active subscriptions.
        """
        invitees_with_active_subscriptions = self.affiliateinvitee_set.filter(
            invitee_discord_id__in=Subscriber.objects.filter(
                subscriptions__status=Subscription.SubscriptionStatus.ACTIVE
            ).values("discord_id")
        )
        return invitees_with_active_subscriptions.count()

    def calculate_total_commissions(self):
        """
        Calculate the sum of all commissions received by the affiliate.
        """
        total_commissions = 0
        invitees = self.affiliateinvitee_set.all()
        for invitee in invitees:
            commission_payment = invitee.get_affiliate_commission_payment()
            total_commissions += commission_payment
        return total_commissions

    def calculate_conversion_rate(self):
        """
        Calculate the conversion rate of the affiliate.
        """
        invitees_count = self.affiliateinvitee_set.count()
        successful_invitees_count = self.affiliateinvitee_set.filter(
            invitee_discord_id__in=Subscriber.objects.filter(
                Q(subscriptions__status=Subscription.SubscriptionStatus.ACTIVE)
                | Q(subscriptions__status=Subscription.SubscriptionStatus.EXPIRED)
            ).values("discord_id")
        ).count()

        if invitees_count > 0:
            conversion_rate = (successful_invitees_count / invitees_count) * 100
        else:
            conversion_rate = 0

        return conversion_rate


class AffiliateInvitee(models.Model):
    """Model table for an Invited user by an Affiliate"""

    affiliate = models.ForeignKey(Affiliate, on_delete=models.CASCADE)
    invitee_discord_id = models.CharField(
        max_length=255, unique=True, help_text="Discord ID of the Invitee"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

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

    def get_invitee_subscription(self):
        """
        Get the latest subscription of the invitee, regardless of its status.
        """
        subscriber = Subscriber.objects.filter(
            discord_id=self.invitee_discord_id
        ).first()
        if subscriber:
            return subscriber.subscriptions.order_by("created").latest()
        return None

    def get_affiliate_commission_payment(self):
        subscriber = Subscriber.objects.filter(
            discord_id=self.invitee_discord_id
        ).first()
        if subscriber:
            subscriptions = subscriber.subscriptions.all()
            commission_payment = 0
            for subscription in subscriptions:
                subscription_amount = subscription.plan.amount
                server_owner = self.affiliate.serverowner
                commission_payment += server_owner.calculate_affiliate_commission(
                    subscription_amount
                )
            return commission_payment
        return 0


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
        help_text="The commission to be paid.",
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

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """
    Model for subscriptions.
    """

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = "A", "Active"
        INACTIVE = "I", "Inactive"
        EXPIRED = "E", "Expired"

    subscriber = models.ForeignKey(
        Subscriber, on_delete=models.CASCADE, related_name="subscriptions"
    )
    subscribed_via = models.ForeignKey(ServerOwner, on_delete=models.CASCADE)
    plan = models.ForeignKey(StripePlan, on_delete=models.CASCADE)
    subscription_date = models.DateTimeField()
    expiration_date = models.DateTimeField(blank=True, null=True)
    subscription_id = models.CharField(max_length=200, blank=True, null=True)
    session_id = models.CharField(max_length=200, blank=True, null=True)
    customer_id = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(
        max_length=1,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INACTIVE,
    )
    value = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        get_latest_by = ["-created"]

    def __str__(self):
        return f"Subscription #{self.id}"


class PaymentDetail(models.Model):
    affiliate = models.OneToOneField(Affiliate, on_delete=models.CASCADE)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment detail for {self.affiliate}"
