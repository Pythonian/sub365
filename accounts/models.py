import uuid
from decimal import ROUND_DOWN, Decimal

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import (
    ActivePlanManager,
    ActiveSubscriptionManager,
    PendingSubscriptionManager,
)


class User(AbstractUser):
    """Custom user model with additional fields."""

    is_serverowner = models.BooleanField(default=False)
    is_subscriber = models.BooleanField(default=False)
    is_affiliate = models.BooleanField(default=False)


class ServerOwner(models.Model):
    """Model representing serverowner instance."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        help_text=_("The Serverowner."),
    )
    discord_id = models.CharField(
        _("discord id"),
        max_length=255,
        unique=True,
        help_text=_("Discord ID of the Serverowner."),
    )
    username = models.CharField(
        _("username"),
        max_length=255,
        unique=True,
        help_text=_("The username of the Serverowner from Discord."),
    )
    avatar = models.CharField(
        _("avatar"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("The ID of the Serverowner's avatar from Discord."),
    )
    subdomain = models.CharField(
        _("subdomain"),
        max_length=20,
        help_text=_("The referral name."),
    )
    email = models.EmailField(
        _("email"),
        help_text=_("Email address of the Serverowner from Discord."),
    )
    stripe_account_id = models.CharField(
        _("stripe account id"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("The stripe account ID of the Serverowner."),
    )
    affiliate_commission = models.IntegerField(
        _("affiliate commission"),
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_("Percentage commission for affiliates."),
    )
    total_pending_commissions = models.DecimalField(
        _("total pending commissions"),
        max_digits=9,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Total pending dollar commissions to be paid by the Serverowner."),
    )
    total_coin_pending_commissions = models.DecimalField(
        _("total coin pending commissions"),
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text=_("Total pending coin commissions to be paid by the Serverowner."),
    )
    coinpayment_api_secret_key = models.CharField(
        _("coinpayment api secret key"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Coinpayment API secret key of the serverowner."),
    )
    coinpayment_api_public_key = models.CharField(
        _("coinpayment api public key"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Coinpayment API public key of the serverowner."),
    )
    coinpayment_onboarding = models.BooleanField(
        _("coinpayment onboarding"),
        default=False,
        help_text=_("If this Serverowner onboarded via coinpayment."),
    )
    stripe_onboarding = models.BooleanField(
        _("stripe onboarding"),
        default=False,
        help_text=_("If this Serverowner onboarded via stripe."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the ServerOwner model."""

        ordering = ["-created"]
        verbose_name = _("serverowner")
        verbose_name_plural = _("serverowners")

    def __str__(self) -> str:
        """Return a string representation of the ServerOwner instance."""
        return self.username

    def get_choice_server(self):
        """Retrieve the choice server marked as True for the ServerOwner.

        Returns:
            Server: The choice server of the ServerOwner marked as True.
        """
        return self.servers.filter(choice_server=True).first()

    # ===== SERVEROWNER PLAN METHODS ===== #

    def get_plans(self):
        """Retrieve the serverowner's plans from the database.

        Returns:
            QuerySet: QuerySet of Plan objects belonging to the serverowner.
        """
        plans_model = self.coinplan_plans if self.coinpayment_onboarding else self.stripeplan_plans
        return plans_model.all()

    def get_plan_count(self):
        """Get the total count of plans created by the serverowner.

        Returns:
            int: The total count of plans created by the serverowner.
        """
        plans_model = self.coinplan_plans if self.coinpayment_onboarding else self.stripeplan_plans
        return plans_model.count()

    def get_active_plans_count(self):
        """Get the total number of active plans.

        Returns:
            int: The total number of active plans.
        """
        PlanModel = CoinPlan if self.coinpayment_onboarding else StripePlan
        return self.get_plans().filter(status=PlanModel.PlanStatus.ACTIVE.value).count()

    def get_inactive_plans_count(self):
        """Get the total number of inactive plans.

        Returns:
            int: The total number of inactive plans.
        """
        PlanModel = CoinPlan if self.coinpayment_onboarding else StripePlan
        return self.get_plans().filter(status=PlanModel.PlanStatus.INACTIVE.value).count()

    def get_popular_plans(self, limit=3):
        """Get the popular plans created by the ServerOwner based on number of subscribers.

        Returns:
            QuerySet: QuerySet of Plan objects ordered by subscriber count
                      in descending order excluding plans with no subscribers.
        """
        PlanModel = CoinPlan if self.coinpayment_onboarding else StripePlan
        return (
            self.get_plans()
            .filter(status=PlanModel.PlanStatus.ACTIVE, subscriber_count__gt=0)
            .order_by(
                "-subscriber_count",
            )[:limit]
        )

    # ===== SERVEROWNER AFFILIATE METHODS ===== #

    def get_total_payments_to_affiliates(self):
        """Get the total payments the serverowner has paid to affiliates.

        Returns:
            Decimal: The total payments the serverowner has paid to affiliates.
        """
        return self.affiliate_set.aggregate(total_payments=Sum("total_commissions_paid")).get(
            "total_payments",
        ) or Decimal(0)

    def get_pending_affiliates(self):
        """Get a list of pending affiliates that the serverowner is to pay.

        Returns:
            QuerySet: QuerySet of Affiliate objects with pending commissions.
        """
        return self.affiliate_set.exclude(pending_commissions=0)

    def get_pending_affiliates_count(self):
        """Get the total number of affiliates who are yet to be paid by serverowner.

        Returns:
            int: The total number of pending affiliates.
        """
        return self.get_pending_affiliates().count()

    def get_affiliates(self):
        """Get a list of all affiliates associated with the serverowner.

        Returns:
            QuerySet: QuerySet of Affiliate objects associated with the serverowner.
        """
        return Affiliate.objects.filter(serverowner=self)

    def get_affiliate_payments(self):
        """Get the list of Affiliate payments associated with the serverowner.

        Returns:
            QuerySet: QuerySet of AffiliatePayment objects associated with the serverowner.
        """
        return AffiliatePayment.objects.filter(serverowner=self)

    def get_pending_affiliate_payments(self):
        """Get the pending commissions the serverowner is to pay affiliates.

        Returns:
            QuerySet: QuerySet of AffiliatePayment objects with pending commissions.
        """
        return self.get_affiliate_payments().filter(paid=False)

    def get_confirmed_affiliate_payments(self):
        """Get the confirmed payment of commissions the serverowner has paid to affiliates.

        Returns:
            QuerySet: QuerySet of AffiliatePayment objects with confirmed payments.
        """
        return self.get_affiliate_payments().filter(paid=True)

    def get_affiliates_confirmed_payment_count(self):
        """Get the total number of affiliates who have been paid by the serverowner.

        Returns:
            int: The total number of affiliates with confirmed payments.
        """
        return self.get_confirmed_affiliate_payments().count()

    def get_confirmed_payment_amount(self):
        """Get the total amount of confirmed payments made by the serverowner to affiliates.

        Returns:
            Decimal: The total amount of confirmed payments.
        """
        confirmed_payments = self.get_confirmed_affiliate_payments()
        total_amount = confirmed_payments.aggregate(total=Sum("amount")).get("total")
        return Decimal(total_amount).quantize(Decimal("0.00")) if total_amount is not None else Decimal("0.00")

    def calculate_affiliate_commission(self, subscription_amount):
        """Calculate the affiliate commission based on the subscription
        amount and affiliate commission percentage.

        Args:
            subscription_amount (float): The subscription amount.

        Returns:
            float: The calculated affiliate commission amount.
        """
        if self.coinpayment_onboarding:
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
        """Retrieve the affiliates associated with the ServerOwner.

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
        """Get the total number of affiliates associated with the ServerOwner.

        Returns:
            int: The total number of affiliates.
        """
        return self.get_affiliates().count()

    # ===== SERVEROWNER SUBSCRIBER METHODS ===== #

    def get_subscribed_users(self):
        """Retrieve the subscribers who subscribed to any of the plans created by the
        ServerOwner.

        Returns:
            QuerySet: QuerySet of Subscriber objects who subscribed via the ServerOwner.
        """
        return Subscriber.objects.filter(subscribed_via=self)

    def get_total_subscribers(self):
        """Get the total number of subscribers who subscribed via the ServerOwner.

        Returns:
            int: The total number of subscribers.
        """
        return self.get_subscribed_users().count()

    # ===== SERVEROWNER SUBSCRIPTION METHODS ===== #

    def get_latest_subscriptions(self, limit=3):
        """Retrieve the latest subscriptions for the ServerOwner.

        Args:
            limit (int): The maximum number of subscriptions to retrieve. Default is 3.

        Returns:
            QuerySet: QuerySet of Subscription objects ordered by creation date.
        """
        SubscriptionModel = CoinSubscription if self.coinpayment_onboarding else StripeSubscription
        return SubscriptionModel.active_subscriptions.filter(
            subscribed_via=self,
        )[:limit]

    def get_total_earnings(self):
        """Calculate the total earnings of the ServerOwner based on subscriptions with
        statuses ACTIVE, EXPIRED, and CANCELED.

        Returns:
            Decimal: The total earnings amount formatted with two decimal places.
        """
        SubscriptionModel = CoinSubscription if self.coinpayment_onboarding else StripeSubscription
        total_earnings = (
            SubscriptionModel.objects.filter(
                subscribed_via=self,
                status__in=[
                    SubscriptionModel.SubscriptionStatus.ACTIVE,
                    SubscriptionModel.SubscriptionStatus.EXPIRED,
                    SubscriptionModel.SubscriptionStatus.CANCELED,
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
        """Get the total number of subscribers with active subscriptions.

        Returns:
            int: The total number of subscribers with active subscriptions.
        """
        if self.coinpayment_onboarding:
            return (
                self.get_subscribed_users()
                .filter(coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE)
                .count()
            )
        else:
            return (
                self.get_subscribed_users()
                .filter(stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.ACTIVE)
                .count()
            )

    def get_inactive_subscribers_count(self):
        """Get the total number of subscribers with inactive subscriptions.

        Returns:
            int: The total number of subscribers with inactive subscriptions.
        """
        if self.coinpayment_onboarding:
            return (
                self.get_subscribed_users()
                .exclude(coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE)
                .count()
            )
        else:
            return (
                self.get_subscribed_users()
                .exclude(stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.ACTIVE)
                .count()
            )


class Server(models.Model):
    """Model representing a discord server instance."""

    owner = models.ForeignKey(
        "ServerOwner",
        on_delete=models.CASCADE,
        related_name="servers",
        verbose_name=_("owner"),
        help_text=_("The Serverowner who owns this Discord server."),
    )
    server_id = models.CharField(
        _("server id"),
        max_length=100,
        help_text=_("The Discord ID of the server."),
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("Name of the server."),
    )
    icon = models.CharField(
        _("icon"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Icon of the server on Discord."),
    )
    choice_server = models.BooleanField(
        _("choice server"),
        default=False,
        help_text=_("If this is the server the Serverowner onboarded with."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the Server model."""

        ordering = ["-created"]
        verbose_name = _("discord server")
        verbose_name_plural = _("discord servers")

    def __str__(self) -> str:
        """Return a string representation of the Server instance."""
        return self.name


class Subscriber(models.Model):
    """Model representing subscribers."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        help_text=_("The associated user for the subscriber."),
    )
    discord_id = models.CharField(
        _("discord id"),
        max_length=255,
        unique=True,
        help_text=_("Discord ID of the subscriber."),
    )
    username = models.CharField(
        _("username"),
        max_length=255,
        unique=True,
        help_text=_("Username of the subscriber."),
    )
    avatar = models.CharField(
        _("avatar"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Avatar URL of the subscriber."),
    )
    email = models.EmailField(
        _("email"),
        help_text=_("Email address of the subscriber."),
    )
    subscribed_via = models.ForeignKey(
        "ServerOwner",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("subscribed via"),
        help_text=_("The serverowner via which the subscriber is subscribed."),
    )
    stripe_customer_id = models.CharField(
        _("stripe customer id"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Stripe customer ID of the subscriber."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the Subscriber model."""

        ordering = ["-created"]
        verbose_name = _("subscriber")
        verbose_name_plural = _("subscribers")

    def __str__(self) -> str:
        """Return a string representation of the Subscriber instance."""
        return self.username

    def get_absolute_url(self):
        """Returns the absolute URL for a subscriber instance."""
        return reverse("subscriber_detail", args=[self.id])

    def has_active_subscription(self):
        """Check if the subscriber has an active subscription.

        Returns:
            bool: True if the subscriber has an active subscription, False otherwise.
        """
        if self.subscribed_via.coinpayment_onboarding:
            return self.coinsubscription_subscriptions.filter(
                status=CoinSubscription.SubscriptionStatus.ACTIVE,
                # expiration_date__gt=timezone.now(),
            ).exists()
        else:
            return self.stripesubscription_subscriptions.filter(
                status=StripeSubscription.SubscriptionStatus.ACTIVE,
                # expiration_date__gt=timezone.now(),
            ).exists()

    def get_latest_pending_subscription(self):
        """Get the latest PENDING subscription of the subscriber.

        Returns:
            Subscription or None: The latest PENDING subscription or None if not found.
        """
        if self.subscribed_via.coinpayment_onboarding:
            subscriptions = self.coinsubscription_subscriptions.filter(
                status=CoinSubscription.SubscriptionStatus.PENDING,
            ).order_by("-created")
        else:
            subscriptions = self.stripesubscription_subscriptions.filter(
                status=StripeSubscription.SubscriptionStatus.PENDING,
            ).order_by(
                "-created",
            )

        if subscriptions.exists():
            return subscriptions.first()
        else:
            return None

    def get_subscriptions(self):
        """Get the subscriptions associated with the subscriber.

        Returns:
            QuerySet: The queryset of subscriptions associated with the subscriber.
        """
        if self.subscribed_via.coinpayment_onboarding:
            return self.coinsubscription_subscriptions.all()
        else:
            return self.stripesubscription_subscriptions.all()


class Affiliate(models.Model):
    """Model representing affiliates."""

    subscriber = models.OneToOneField(
        Subscriber,
        on_delete=models.CASCADE,
        verbose_name=_("subscriber"),
        help_text=_("The subscriber associated with the affiliate."),
    )
    affiliate_link = models.CharField(
        _("affiliate link"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text=_("The unique affiliate link."),
    )
    discord_id = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name=_("discord id"),
        help_text=_("Discord ID of the affiliate."),
    )
    server_id = models.CharField(
        _("server id"),
        max_length=255,
        help_text=_("The ID of the server associated with the affiliate."),
    )
    serverowner = models.ForeignKey(
        "ServerOwner",
        on_delete=models.CASCADE,
        verbose_name=_("server owner"),
        help_text=_("The server owner associated with the affiliate."),
    )
    last_payment_date = models.DateTimeField(
        _("last payment date"),
        null=True,
        blank=True,
        help_text=_("The date and time of the last payment to the affiliate."),
    )
    total_commissions_paid = models.DecimalField(
        _("total commissions paid"),
        max_digits=9,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Total commissions paid to the affiliate."),
    )
    total_coin_commissions_paid = models.DecimalField(
        _("total coin commissions paid"),
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text=_("Total coin commissions paid to the affiliate."),
    )
    pending_commissions = models.DecimalField(
        _("pending commissions"),
        max_digits=9,
        decimal_places=2,
        default=0,
        help_text=_("Pending commissions to be paid to the affiliate."),
    )
    pending_coin_commissions = models.DecimalField(
        _("pending coin commissions"),
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text=_("Pending coin commissions to be paid to the affiliate."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the Affiliate model."""

        ordering = ["-created"]

    def __str__(self) -> str:
        """Return a string representation of the Affiliate instance."""
        return self.subscriber.username

    def get_absolute_url(self):
        """Returns the absolute URL for an affiliate instance."""
        return reverse("affiliate_detail", args=[self.subscriber.id])

    def update_last_payment_date(self):
        """Update the last payment date of the affiliate to the current date and time."""
        self.last_payment_date = timezone.now()
        self.save()

    def get_total_invitation_count(self):
        """Get the total count of affiliate invitees.

        Returns:
            int: The total count of affiliate invitees.
        """
        return self.affiliateinvitee_set.all().count()

    def get_active_subscription_count(self):
        """Get the count of invitees with active subscriptions.

        Returns:
            int: The count of invitees with active subscriptions.
        """
        if self.serverowner.coinpayment_onboarding:
            invitees_with_active_coin_subscriptions = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE,
                ).values("discord_id"),
            )
            return invitees_with_active_coin_subscriptions.count()
        else:
            invitees_with_active_stripe_subscriptions = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.ACTIVE,
                ).values("discord_id"),
            )
            return invitees_with_active_stripe_subscriptions.count()

    def calculate_conversion_rate(self):
        """Calculate the conversion rate of the affiliate.

        Returns:
            float: The conversion rate of the affiliate.
        """
        invitees_count = self.affiliateinvitee_set.count()
        if self.serverowner.coinpayment_onboarding:
            successful_invitees_count = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    Q(coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.ACTIVE)
                    | Q(coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.CANCELED)
                    | Q(coinsubscription_subscriptions__status=CoinSubscription.SubscriptionStatus.EXPIRED),
                ).values("discord_id"),
            ).count()
        else:
            successful_invitees_count = self.affiliateinvitee_set.filter(
                invitee_discord_id__in=Subscriber.objects.filter(
                    Q(stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.ACTIVE)
                    | Q(stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.CANCELED)
                    | Q(stripesubscription_subscriptions__status=StripeSubscription.SubscriptionStatus.EXPIRED),
                ).values("discord_id"),
            ).count()

        if invitees_count > 0:
            conversion_rate = (successful_invitees_count / invitees_count) * 100
        else:
            conversion_rate = 0

        return round(conversion_rate, 2)

    def get_affiliate_payments(self):
        """Get the affiliate payments associated with this affiliate.

        Returns:
            QuerySet: The queryset of affiliate payments associated with this affiliate.
        """
        return AffiliatePayment.objects.filter(affiliate=self)

    def get_affiliate_invitees(self):
        """Get a list of all affiliate invitees associated with this affiliate.

        Returns:
            QuerySet: The queryset of affiliate invitees associated with this affiliate.
        """
        return self.affiliateinvitee_set.all()


class AffiliateInvitee(models.Model):
    """Model representing Affiliate invitee."""

    affiliate = models.ForeignKey(
        "Affiliate",
        on_delete=models.CASCADE,
        verbose_name=_("affiliate"),
        help_text=_("The affiliate who invited the user."),
    )
    invitee_discord_id = models.CharField(
        _("invitee discord id"),
        max_length=255,
        unique=True,
        help_text=_("Discord ID of the Invitee."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the AffiliateInvitee model."""

        ordering = ["-id"]
        verbose_name = _("affiliate invitee")
        verbose_name_plural = _("affiliate invitees")

    def __str__(self) -> str:
        """Return a string representation of the AffiliateInvitee instance."""
        return self.invitee_discord_id

    def get_affiliateinvitee_name(self):
        """Get the username of the Invitee.

        Returns:
            str or None: The username of the invitee, or None if not found.
        """
        subscriber = Subscriber.objects.filter(discord_id=self.invitee_discord_id).first()
        if subscriber:
            return subscriber.username
        return None

    def get_affiliate_commission_payment(self):
        """Get the affiliate commission payment received for this Invitee.

        Returns:
            Decimal: The affiliate commission payment received.
        """
        subscriber = Subscriber.objects.filter(discord_id=self.invitee_discord_id).first()
        if subscriber:
            if self.affiliate.serverowner.coinpayment_onboarding:
                subscription = subscriber.coinsubscription_subscriptions.order_by("-created").first()
                if subscription:
                    subscription_amount = subscription.plan.amount
                    serverowner = self.affiliate.serverowner
                    return serverowner.calculate_affiliate_commission(subscription_amount)
            else:
                subscription = subscriber.stripesubscription_subscriptions.order_by("-created").first()
                if subscription:
                    subscription_amount = subscription.plan.amount
                    serverowner = self.affiliate.serverowner
                    return serverowner.calculate_affiliate_commission(subscription_amount)
        return Decimal(0)

    def get_affiliate_coin_commission_payment(self):
        subscriber = Subscriber.objects.filter(discord_id=self.invitee_discord_id).first()
        if subscriber and self.affiliate.serverowner.coinpayment_onboarding:
            subscription = subscriber.coinsubscription_subscriptions.order_by("-created").first()
            if subscription:
                subscription_amount = subscription.coin_amount
                serverowner = self.affiliate.serverowner
                return serverowner.calculate_affiliate_commission(subscription_amount)
        return 0

    def calculate_affiliate_payment_commission(self):
        """Calculate the total affiliate payment commission received for this AffiliateInvitee.

        Returns:
            Decimal: The total affiliate payment commission received.
        """
        affiliate_payments = AffiliatePayment.objects.filter(
            affiliate=self.affiliate,
            subscriber__discord_id=self.invitee_discord_id,
            paid=True,
        )
        total_commission = affiliate_payments.aggregate(total_commission=Sum("amount")).get("total_commission")
        return total_commission or Decimal(0)


class AffiliatePayment(models.Model):
    """Model representing Affiliate payments."""

    serverowner = models.ForeignKey(
        "ServerOwner",
        on_delete=models.CASCADE,
        verbose_name=_("serverowner"),
        help_text=_("The serverowner who is to pay the affiliate."),
    )
    affiliate = models.ForeignKey(
        "Affiliate",
        on_delete=models.CASCADE,
        verbose_name=_("affiliate"),
        help_text=_("Discord ID of the Affiliate to be paid."),
    )
    subscriber = models.ForeignKey(
        "Subscriber",
        on_delete=models.CASCADE,
        verbose_name=_("subscriber"),
        help_text=_("The Affiliate Invitee who subscribed."),
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text=_("The dollar commission to be paid."),
    )
    coin_amount = models.DecimalField(
        _("coin amount"),
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
        help_text=_("The coin commission to be paid."),
    )
    paid = models.BooleanField(
        _("paid"),
        default=False,
        help_text=_("If this payment has been made."),
    )
    date_payment_confirmed = models.DateTimeField(
        _("date payment confirmed"),
        blank=True,
        null=True,
        help_text=_("Date the serverowner made payment."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the AffiliatePayment model."""

        ordering = ["-created"]
        verbose_name = _("affiliate payment")
        verbose_name_plural = _("affiliate payments")

    def __str__(self) -> str:
        """Return a string representation of the affiliatepayment."""
        return f"#{self.id}"


class BasePlan(models.Model):
    """Base Model for Subscription plans."""

    class PlanStatus(models.TextChoices):
        """Choices for the plan status."""

        ACTIVE = "A", _("Active")
        INACTIVE = "I", _("Inactive")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    serverowner = models.ForeignKey(
        "ServerOwner",
        on_delete=models.CASCADE,
        related_name="%(class)s_plans",
        verbose_name=_("serverowner"),
        help_text=_("The serverowner who created the plan."),
    )
    name = models.CharField(
        _("name"),
        max_length=100,
        help_text=_("The name of the plan."),
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=9,
        decimal_places=2,
        help_text=_("The amount in dollars for the plan."),
        validators=[MinValueValidator(0)],
    )
    description = models.TextField(
        _("description"),
        max_length=300,
        help_text=_("Description of the plan (up to 300 characters)."),
    )
    interval_count = models.IntegerField(
        _("interval count"),
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text=_("Number of months the plan should last."),
    )
    subscriber_count = models.IntegerField(
        _("subscriber count"),
        default=0,
        help_text=_("The number of subscribers to this plan."),
    )
    status = models.CharField(
        _("status"),
        max_length=1,
        choices=PlanStatus.choices,
        default=PlanStatus.ACTIVE,
        help_text=_("Status of the plan."),
    )
    discord_role_id = models.CharField(
        _("discord role id"),
        max_length=255,
        help_text=_("ID of Discord role to be assigned to subscribers."),
    )
    permission_description = models.CharField(
        _("permission description"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Description of permissions to be given to subscribers."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active_plans = ActivePlanManager()

    class Meta:
        abstract = True

    def __str__(self) -> str:
        """Return a string representation of the plan."""
        return self.name

    def get_absolute_url(self):
        """Returns the absolute URL for a plan instance."""
        return reverse("plan_detail", args=[self.id])


class StripePlan(BasePlan):
    """Model representing Stripe plans."""

    product_id = models.CharField(
        _("product id"),
        max_length=100,
        help_text=_("The product ID associated with the plan."),
    )
    price_id = models.CharField(
        _("price id"),
        max_length=100,
        help_text=_("The price ID associated with the plan."),
    )

    class Meta:
        """Metadata options for the StripePlan model."""

        ordering = ["-created"]
        verbose_name = _("stripe plan")
        verbose_name_plural = _("stripe plans")

    def total_earnings(self):
        """Calculate the total earnings from subscriptions to this plan.

        Returns:
            Decimal: The total earnings from subscriptions.
        """
        subscribers = StripeSubscription.objects.filter(plan=self, subscribed_via=self.serverowner)
        total_earnings = subscribers.aggregate(total=models.Sum("plan__amount"))["total"]
        return total_earnings or Decimal(0)

    def get_plan_subscribers(self):
        """Get all subscribers for this plan, filtered by the server owner.

        Returns:
            QuerySet: A queryset of subscribers for this plan and serverowner.
        """
        return StripeSubscription.objects.filter(plan=self, subscribed_via=self.serverowner)

    def active_subscriptions_count(self):
        """Count the number of active subscriptions for this plan.

        Returns:
            int: The count of active subscriptions.
        """
        subscribers = self.get_plan_subscribers()
        active_subscriptions = subscribers.filter(status=StripeSubscription.SubscriptionStatus.ACTIVE)
        return active_subscriptions.count()

    def total_subscriptions_count(self):
        """Count the total number of subscriptions for this plan.

        Returns:
            int: The total count of subscriptions.
        """
        subscribers = self.get_plan_subscribers()
        return subscribers.count()


class CoinPlan(BasePlan):
    """Model representing Coinpayment plans."""

    class Meta:
        """Metadata options for the CoinPlan model."""

        ordering = ["-created"]
        verbose_name = _("coin plan")
        verbose_name_plural = _("coin plans")

    def total_earnings(self):
        """Calculate the total earnings from subscriptions to this plan.

        Returns:
            Decimal: The total earnings from subscriptions.
        """
        subscribers = CoinSubscription.objects.filter(plan=self, subscribed_via=self.serverowner)
        total_earnings = subscribers.aggregate(total=models.Sum("plan__amount"))["total"]
        return total_earnings or Decimal(0)

    def get_plan_subscribers(self):
        """Get all subscribers for this plan, filtered by the server owner.

        Returns:
            QuerySet: A queryset of subscribers for this plan and serverowner.
        """
        return CoinSubscription.objects.filter(plan=self, subscribed_via=self.serverowner)

    def active_subscriptions_count(self):
        """Count the number of active subscriptions for this plan.

        Returns:
            int: The count of active subscriptions.
        """
        subscribers = self.get_plan_subscribers()
        active_subscriptions = subscribers.filter(status=CoinSubscription.SubscriptionStatus.ACTIVE)
        return active_subscriptions.count()

    def total_subscriptions_count(self):
        """Count the total number of subscriptions for this plan.

        Returns:
            int: The total count of subscriptions.
        """
        subscribers = self.get_plan_subscribers()
        return subscribers.count()


class BaseSubscription(models.Model):
    """Base model for subscriptions."""

    class SubscriptionStatus(models.TextChoices):
        """Choices for the subscription status."""

        ACTIVE = "A", _("Active")
        PENDING = "P", _("Pending")
        EXPIRED = "E", _("Expired")
        CANCELED = "C", _("Canceled")

    subscriber = models.ForeignKey(
        "Subscriber",
        on_delete=models.CASCADE,
        related_name="%(class)s_subscriptions",
        verbose_name=_("subscriber"),
        help_text=_("The user subscribing to the plan."),
    )
    subscribed_via = models.ForeignKey(
        "ServerOwner",
        on_delete=models.CASCADE,
        verbose_name=_("subscribed via"),
        help_text=_("The serverowner for whom this subscription is intended."),
    )
    subscription_id = models.CharField(
        _("subscription id"),
        max_length=225,
        blank=True,
        help_text=_("The subscription ID associated with this subscription."),
    )
    subscription_date = models.DateTimeField(
        _("subscription date"),
        blank=True,
        null=True,
        help_text=_("The date and time when the subscription was initiated."),
    )
    expiration_date = models.DateTimeField(
        _("expiration date"),
        blank=True,
        null=True,
        help_text=_("The date and time when the subscription will expire."),
    )
    status = models.CharField(
        _("status"),
        max_length=1,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
        help_text=_("The status of the subscription."),
    )
    value = models.IntegerField(
        _("value"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active_subscriptions = ActiveSubscriptionManager()
    pending_subscriptions = PendingSubscriptionManager()

    class Meta:
        """Metadata options for the Subscription model."""

        abstract = True
        ordering = ["-created"]
        get_latest_by = ["-created"]

    def __str__(self) -> str:
        """Return a string representation of the subscription."""
        return f"#{self.id}"

    def save(self, *args, **kwargs):
        if self.status == self.SubscriptionStatus.ACTIVE:
            # Check if the subscriber already has an active subscription
            if self.subscriber.has_active_subscription():
                msg = "Subscriber already has an active subscription."
                raise ValidationError(msg)
        super().save(*args, **kwargs)


class StripeSubscription(BaseSubscription):
    """Model representing Stripe subscriptions."""

    plan = models.ForeignKey(
        "StripePlan",
        on_delete=models.CASCADE,
        verbose_name=_("plan"),
        help_text=_("The Stripe plan being subscribed to."),
    )
    session_id = models.CharField(
        _("session id"),
        max_length=200,
        blank=True,
        help_text=_("The Stripe checkout session ID associated with this subscription."),
    )

    class Meta(BaseSubscription.Meta):
        """Metadata options for the Subscription model."""

        verbose_name = _("stripe subscription")
        verbose_name_plural = _("stripe subscriptions")


class CoinSubscription(BaseSubscription):
    """Model representing subscriptions for coin plans."""

    plan = models.ForeignKey(
        "CoinPlan",
        on_delete=models.CASCADE,
        verbose_name=_("plan"),
        help_text=_("The coin plan being subscribed to."),
    )
    coin_amount = models.DecimalField(
        _("coin amount"),
        max_digits=20,
        decimal_places=8,
        blank=True,
        null=True,
        help_text=_("The litecoin value associated with the subscription."),
    )
    address = models.CharField(
        _("address"),
        max_length=225,
        blank=True,
        help_text=_("The Litecoin address associated with the subscription."),
    )
    checkout_url = models.CharField(
        _("checkout url"),
        max_length=225,
        blank=True,
        help_text=_("The CoinPayment URL for subscriber redirection."),
    )
    status_url = models.CharField(
        _("status url"),
        max_length=225,
        blank=True,
        help_text=_("The URL for accessing transaction status information."),
    )

    class Meta(BaseSubscription.Meta):
        """Metadata options for the CoinSubscription model."""

        verbose_name = _("coin subscription")
        verbose_name_plural = _("coin subscriptions")


class PaymentDetail(models.Model):
    """Model to store payment details of an affiliate."""

    affiliate = models.OneToOneField(
        Affiliate,
        on_delete=models.CASCADE,
        verbose_name=_("affiliate"),
        help_text=_("The affiliate user linked to this payment detail."),
    )
    litecoin_address = models.CharField(
        _("litecoin address"),
        max_length=255,
        blank=True,
        help_text=_("The Litecoin address of the affiliate, used when registered via CoinPayments."),
    )
    body = models.TextField(
        _("payment information"),
        blank=True,
        max_length=300,
        help_text=_("Payment details of the affiliate when registered via Stripe."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the PaymentDetail model."""

        verbose_name = _("payment detail")

    def __str__(self) -> str:
        """Return a string representation of the payment detail."""
        return f"{self.affiliate}"


class AccessCode(models.Model):
    """Model representing unique access codes for dashboard access."""

    code = models.CharField(
        _("code"),
        max_length=5,
        unique=True,
        help_text=_("The unique access code value."),
    )
    used_by = models.ForeignKey(
        "ServerOwner",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("used by"),
        help_text=_("The serverowner who used the access code."),
    )
    is_used = models.BooleanField(
        _("is used?"),
        default=False,
        help_text=_("Whether the access code has been used."),
    )
    date_used = models.DateTimeField(
        _("date used"),
        blank=True,
        null=True,
        help_text=_("The date and time the access code was used."),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the AccessCode model."""

        ordering = ["-created"]
        verbose_name = _("access code")
        verbose_name_plural = _("access codes")

    def __str__(self) -> str:
        """Return a string representation of the access code."""
        return self.code
