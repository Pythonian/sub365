from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from ..models import (
    CoinPlan,
    CoinSubscription,
    ServerOwner,
    StripePlan,
    StripeSubscription,
    Subscriber,
    User,
)


class SubscriptionManagerTestCase(TestCase):
    """Test case for the Subscription Manager."""

    def setUp(self):
        """Set up initial data for the test."""
        # Create or retrieve a user
        self.user, _ = User.objects.get_or_create(
            username="Pythonian",
            is_serverowner=True,
        )
        # Create a server owner
        self.server_owner, _ = ServerOwner.objects.get_or_create(
            user=self.user,
            defaults={
                "discord_id": "123456789",
                "username": "Pythonian",
                "subdomain": "prontomaster",
                "email": "pythonian@gmail.com",
            },
        )

        # Create a subscriber
        self.subscriber_user, _ = User.objects.get_or_create(
            username="Madabevel",
            is_subscriber=True,
        )
        self.subscriber, _ = Subscriber.objects.get_or_create(
            user=self.subscriber_user,
            defaults={
                "discord_id": "987654321",
                "username": "Madabevel",
                "email": "madabevel@gmail.com",
                "subscribed_via": self.server_owner,
            },
        )

        # Create a Stripe plan
        self.stripe_plan = StripePlan.objects.create(
            serverowner=self.server_owner,
            name="Test Stripe Plan",
            amount=10.00,
            description="Test Stripe Plan Description",
            interval_count=1,
            discord_role_id="123456789",
            permission_description="Test permission description",
        )

        # Create a Coin plan
        self.coin_plan = CoinPlan.objects.create(
            serverowner=self.server_owner,
            name="Test Coin Plan",
            amount=20.00,
            description="Test Coin Plan Description",
            interval_count=1,
            discord_role_id="987654321",
            permission_description="Test coin permission description",
        )

        # Create active Stripe subscription
        self.active_stripe_subscription = StripeSubscription.objects.create(
            subscriber=self.subscriber,
            subscribed_via=self.server_owner,
            plan=self.stripe_plan,
            subscription_id="stripe_subscription_id_1",
            subscription_date=timezone.now(),
            expiration_date=timezone.now() + timezone.timedelta(days=30),
            status=StripeSubscription.SubscriptionStatus.ACTIVE,
        )

        # Create pending Stripe subscription
        self.pending_stripe_subscription = StripeSubscription.objects.create(
            subscriber=self.subscriber,
            subscribed_via=self.server_owner,
            plan=self.stripe_plan,
            subscription_id="stripe_subscription_id_2",
            subscription_date=timezone.now(),
            status=StripeSubscription.SubscriptionStatus.PENDING,
        )

        # Create active Coin subscription
        self.active_coin_subscription = CoinSubscription.objects.create(
            subscriber=self.subscriber,
            subscribed_via=self.server_owner,
            plan=self.coin_plan,
            subscription_id="coin_subscription_id_1",
            subscription_date=timezone.now(),
            expiration_date=timezone.now() + timezone.timedelta(days=30),
            status=CoinSubscription.SubscriptionStatus.ACTIVE,
            coin_amount=Decimal("0.5"),
            address="test_address_1",
            checkout_url="http://example.com/checkout/1",
            status_url="http://example.com/status/1",
        )

        # Create pending Coin subscription
        self.pending_coin_subscription = CoinSubscription.objects.create(
            subscriber=self.subscriber,
            subscribed_via=self.server_owner,
            plan=self.coin_plan,
            subscription_id="coin_subscription_id_2",
            subscription_date=timezone.now(),
            status=CoinSubscription.SubscriptionStatus.PENDING,
            coin_amount=Decimal("1.0"),
            address="test_address_2",
            checkout_url="http://example.com/checkout/2",
            status_url="http://example.com/status/2",
        )

    def test_active_stripe_subscriptions(self):
        """Test active Stripe subscriptions."""
        active_subscriptions = StripeSubscription.active_subscriptions.all()
        self.assertEqual(active_subscriptions.count(), 1)
        self.assertEqual(active_subscriptions[0], self.active_stripe_subscription)

    def test_pending_stripe_subscriptions(self):
        """Test pending Stripe subscriptions."""
        pending_subscriptions = StripeSubscription.pending_subscriptions.all()
        self.assertEqual(pending_subscriptions.count(), 1)
        self.assertEqual(pending_subscriptions[0], self.pending_stripe_subscription)

    def test_active_coin_subscriptions(self):
        """Test active Coin subscriptions."""
        active_subscriptions = CoinSubscription.active_subscriptions.all()
        self.assertEqual(active_subscriptions.count(), 1)
        self.assertEqual(active_subscriptions[0], self.active_coin_subscription)

    def test_pending_coin_subscriptions(self):
        """Test pending Coin subscriptions."""
        pending_subscriptions = CoinSubscription.pending_subscriptions.all()
        self.assertEqual(pending_subscriptions.count(), 1)
        self.assertEqual(pending_subscriptions[0], self.pending_coin_subscription)


class ActivePlanManagerTestCase(TestCase):
    """Test case for the Active Plans Manager."""

    def setUp(self):
        """Set up initial data for the test."""
        # Create or retrieve a user
        self.user, _ = User.objects.get_or_create(username="Pythonian")

        # Create a server owner
        self.server_owner, _ = ServerOwner.objects.get_or_create(
            user=self.user,
            defaults={
                "discord_id": "123456789",
                "username": "Pythonian",
                "subdomain": "prontomaster",
                "email": "pythonian@gmail.com",
            },
        )

        # Create active and inactive plans for testing
        self.active_stripe_plan = StripePlan.objects.create(
            serverowner=self.server_owner,
            name="Active Plan",
            amount=10.00,
            description="Test active plan",
            interval_count=1,
            discord_role_id="123456789",
            permission_description="Test permission description",
            created=timezone.now(),
        )
        self.inactive_stripe_plan = StripePlan.objects.create(
            serverowner=self.server_owner,
            name="Inactive Plan",
            amount=20.00,
            description="Test inactive plan",
            interval_count=1,
            status=StripePlan.PlanStatus.INACTIVE,
            discord_role_id="987654321",
            permission_description="Test inactive permission description",
            created=timezone.now(),
        )

        self.active_coin_plan = CoinPlan.objects.create(
            serverowner=self.server_owner,
            name="Active Coin Plan",
            amount=30.00,
            description="Test active coin plan",
            interval_count=1,
            discord_role_id="987654321",
            permission_description="Test coin permission description",
            created=timezone.now(),
        )
        self.inactive_coin_plan = CoinPlan.objects.create(
            serverowner=self.server_owner,
            name="Inactive Coin Plan",
            amount=40.00,
            description="Test inactive coin plan",
            interval_count=1,
            status=CoinPlan.PlanStatus.INACTIVE,
            discord_role_id="123456789",
            permission_description="Test inactive coin permission description",
            created=timezone.now(),
        )

    def test_active_stripe_plan_manager(self):
        """Test active Stripe plan manager."""
        active_plans = StripePlan.active_plans.all()
        self.assertEqual(active_plans.count(), 1)
        self.assertEqual(active_plans[0], self.active_stripe_plan)

    def test_active_coin_plan_manager(self):
        """Test active Coin plan manager."""
        active_plans = CoinPlan.active_plans.all()
        self.assertEqual(active_plans.count(), 1)
        self.assertEqual(active_plans[0], self.active_coin_plan)

    def test_inactive_plans_not_in_active_manager(self):
        """Test that inactive plans are not included in the active plan manager."""
        active_stripe_plans = StripePlan.active_plans.all()
        self.assertNotIn(self.inactive_stripe_plan, active_stripe_plans)
        active_coin_plans = CoinPlan.active_plans.all()
        self.assertNotIn(self.inactive_coin_plan, active_coin_plans)
