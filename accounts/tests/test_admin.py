"""Test cases for the admin classes."""

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from accounts.admin import (
    AffiliateInviteeInline,
    AffiliatePaymentInline,
    CoinPlanInline,
    CoinSubscriptionInline,
    PaymentDetailInline,
    ServerInline,
    StripePlanInline,
    StripeSubscriptionInline,
)
from accounts.models import (
    AffiliateInvitee,
    AffiliatePayment,
    CoinPlan,
    CoinSubscription,
    PaymentDetail,
    Server,
    StripePlan,
    StripeSubscription,
)


class ServerInlineTestCase(TestCase):
    """Test case for the ServerInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the ServerInline class."""
        # Instantiate ServerInline with the admin site
        server_inline = ServerInline(Server, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(server_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the ServerInline class."""
        # Instantiate ServerInline with the admin site
        server_inline = ServerInline(Server, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(server_inline.has_add_permission(None))


class StripePlanInlineTestCase(TestCase):
    """Test case for the StripePlanInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the StripePlanInline class."""
        # Instantiate StripePlanInline with the admin site
        stripe_plan_inline = StripePlanInline(StripePlan, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(stripe_plan_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the StripePlanInline class."""
        # Instantiate StripePlanInline with the admin site
        stripe_plan_inline = StripePlanInline(StripePlan, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(stripe_plan_inline.has_add_permission(None))


class CoinPlanInlineTestCase(TestCase):
    """Test case for the CoinPlanInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the CoinPlanInline class."""
        # Instantiate CoinPlanInline with the admin site
        coin_plan_inline = CoinPlanInline(CoinPlan, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(coin_plan_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the CoinPlanInline class."""
        # Instantiate CoinPlanInline with the admin site
        coin_plan_inline = CoinPlanInline(CoinPlan, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(coin_plan_inline.has_add_permission(None))


class CoinSubscriptionInlineTestCase(TestCase):
    """Test case for the CoinSubscriptionInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the CoinSubscriptionInline class."""
        # Instantiate CoinSubscriptionInline with the admin site
        coin_subscription_inline = CoinSubscriptionInline(
            CoinSubscription,
            self.admin_site,
        )

        # Test has_delete_permission method
        self.assertFalse(coin_subscription_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the CoinSubscriptionInline class."""
        # Instantiate CoinSubscriptionInline with the admin site
        coin_subscription_inline = CoinSubscriptionInline(
            CoinSubscription,
            self.admin_site,
        )

        # Test has_add_permission method
        self.assertFalse(coin_subscription_inline.has_add_permission(None))


class StripeSubscriptionInlineTestCase(TestCase):
    """Test case for the StripeSubscriptionInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the StripeSubscriptionInline class."""
        # Instantiate StripeSubscriptionInline with the admin site
        stripe_subscription_inline = StripeSubscriptionInline(
            StripeSubscription,
            self.admin_site,
        )

        # Test has_delete_permission method
        self.assertFalse(stripe_subscription_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the StripeSubscriptionInline class."""
        # Instantiate StripeSubscriptionInline with the admin site
        stripe_subscription_inline = StripeSubscriptionInline(
            StripeSubscription,
            self.admin_site,
        )

        # Test has_add_permission method
        self.assertFalse(stripe_subscription_inline.has_add_permission(None))


class PaymentDetailInlineTestCase(TestCase):
    """Test case for the PaymentDetailInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the PaymentDetailInline class."""
        # Instantiate PaymentDetailInline with the admin site
        paymentdetail_inline = PaymentDetailInline(PaymentDetail, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(paymentdetail_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the PaymentDetailInline class."""
        # Instantiate PaymentDetailInline with the admin site
        paymentdetail_inline = PaymentDetailInline(PaymentDetail, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(paymentdetail_inline.has_add_permission(None))


class AffiliatePaymentInlineTestCase(TestCase):
    """Test case for the AffiliatePaymentInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the AffiliatePaymentInline class."""
        # Instantiate AffiliatePaymentInline with the admin site
        affiliatepayment_inline = AffiliatePaymentInline(
            AffiliatePayment,
            self.admin_site,
        )

        # Test has_delete_permission method
        self.assertFalse(affiliatepayment_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the AffiliatePaymentInline class."""
        # Instantiate AffiliatePaymentInline with the admin site
        affiliatepayment_inline = AffiliatePaymentInline(
            AffiliatePayment,
            self.admin_site,
        )

        # Test has_add_permission method
        self.assertFalse(affiliatepayment_inline.has_add_permission(None))


class AffiliateInviteeInlineTestCase(TestCase):
    """Test case for the AffiliateInviteeInline admin inline class."""

    def setUp(self) -> None:
        """Set up the test environment."""
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self) -> None:
        """Test the has_delete_permission method of the AffiliateInviteeInline class."""
        # Instantiate AffiliateInviteeInline with the admin site
        affiliateinvitee_inline = AffiliateInviteeInline(
            AffiliateInvitee,
            self.admin_site,
        )

        # Test has_delete_permission method
        self.assertFalse(affiliateinvitee_inline.has_delete_permission(None))

    def test_has_add_permission(self) -> None:
        """Test the has_add_permission method of the AffiliateInviteeInline class."""
        # Instantiate AffiliateInviteeInline with the admin site
        affiliateinvitee_inline = AffiliateInviteeInline(
            AffiliateInvitee,
            self.admin_site,
        )

        # Test has_add_permission method
        self.assertFalse(affiliateinvitee_inline.has_add_permission(None))
