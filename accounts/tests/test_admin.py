from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from ..admin import (
    AffiliateInviteeInline,
    AffiliatePaymentInline,
    CoinPlanInline,
    CoinSubscriptionInline,
    PaymentDetailInline,
    ServerInline,
    StripePlanInline,
    StripeSubscriptionInline,
)
from ..models import (
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
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate ServerInline with the admin site
        server_inline = ServerInline(Server, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(server_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate ServerInline with the admin site
        server_inline = ServerInline(Server, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(server_inline.has_add_permission(None))


class StripePlanInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate StripePlanInline with the admin site
        stripe_plan_inline = StripePlanInline(StripePlan, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(stripe_plan_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate StripePlanInline with the admin site
        stripe_plan_inline = StripePlanInline(StripePlan, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(stripe_plan_inline.has_add_permission(None))


class CoinPlanInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate CoinPlanInline with the admin site
        coin_plan_inline = CoinPlanInline(CoinPlan, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(coin_plan_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate CoinPlanInline with the admin site
        coin_plan_inline = CoinPlanInline(CoinPlan, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(coin_plan_inline.has_add_permission(None))


class CoinSubscriptionInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate CoinSubscriptionInline with the admin site
        coin_subscription_inline = CoinSubscriptionInline(CoinSubscription, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(coin_subscription_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate CoinSubscriptionInline with the admin site
        coin_subscription_inline = CoinSubscriptionInline(CoinSubscription, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(coin_subscription_inline.has_add_permission(None))


class StripeSubscriptionInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate StripeSubscriptionInline with the admin site
        stripe_subscription_inline = StripeSubscriptionInline(StripeSubscription, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(stripe_subscription_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate StripeSubscriptionInline with the admin site
        stripe_subscription_inline = StripeSubscriptionInline(StripeSubscription, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(stripe_subscription_inline.has_add_permission(None))


class PaymentDetailInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate PaymentDetailInline with the admin site
        paymentdetail_inline = PaymentDetailInline(PaymentDetail, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(paymentdetail_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate PaymentDetailInline with the admin site
        paymentdetail_inline = PaymentDetailInline(PaymentDetail, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(paymentdetail_inline.has_add_permission(None))


class AffiliatePaymentInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate AffiliatePaymentInline with the admin site
        affiliatepayment_inline = AffiliatePaymentInline(AffiliatePayment, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(affiliatepayment_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate AffiliatePaymentInline with the admin site
        affiliatepayment_inline = AffiliatePaymentInline(AffiliatePayment, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(affiliatepayment_inline.has_add_permission(None))


class AffiliateInviteeInlineTestCase(TestCase):
    def setUp(self):
        # Create an admin site
        self.admin_site = AdminSite()

    def test_has_delete_permission(self):
        # Instantiate AffiliateInviteeInline with the admin site
        affiliateinvitee_inline = AffiliateInviteeInline(AffiliateInvitee, self.admin_site)

        # Test has_delete_permission method
        self.assertFalse(affiliateinvitee_inline.has_delete_permission(None))

    def test_has_add_permission(self):
        # Instantiate AffiliateInviteeInline with the admin site
        affiliateinvitee_inline = AffiliateInviteeInline(AffiliateInvitee, self.admin_site)

        # Test has_add_permission method
        self.assertFalse(affiliateinvitee_inline.has_add_permission(None))
