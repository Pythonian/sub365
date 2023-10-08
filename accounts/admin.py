from django.contrib import admin
from django.contrib.auth.models import Group

from .models import (
    AccessCode,
    Affiliate,
    AffiliateInvitee,
    AffiliatePayment,
    CoinPlan,
    CoinSubscription,
    PaymentDetail,
    Server,
    ServerOwner,
    StripePlan,
    StripeSubscription,
    Subscriber,
    User,
)


@admin.register(AccessCode)
class AccessCode(admin.ModelAdmin):
    """Admin class for managing AccessCode instances."""

    list_display = ["code", "used_by", "is_used", "date_used"]
    list_filter = ["is_used"]


class ServerInline(admin.TabularInline):
    """Inline admin class for managing Discord Server instances within the Serverowner admin."""

    model = Server
    extra = 0
    readonly_fields = ["name", "server_id", "icon", "choice_server"]

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete Server instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new Server instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


class StripePlanInline(admin.StackedInline):
    """Inline admin class for managing StripePlan instances within the Serverowner admin."""

    model = StripePlan
    extra = 0
    view_on_site = False
    readonly_fields = [
        "name",
        "product_id",
        "price_id",
        "amount",
        "description",
        "interval_count",
        "subscriber_count",
        "status",
        "discord_role_id",
        "permission_description",
    ]

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete StripePlan instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new StripePlan instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


class CoinPlanInline(admin.StackedInline):
    """Inline admin class for managing CoinPlan instances within the Serverowner admin."""

    model = CoinPlan
    extra = 0
    view_on_site = False

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete CoinPlan instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new CoinPlan instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


@admin.register(ServerOwner)
class ServerOwnerAdmin(admin.ModelAdmin):
    """Admin class for managing ServerOwner instances."""

    list_display = ["username", "subdomain", "email", "affiliate_commission"]
    search_fields = ["username", "subdomain", "email"]
    search_help_text = "Search by username, referral name or email"
    list_filter = ["stripe_onboarding", "coinpayment_onboarding"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "username",
                    "email",
                    "discord_id",
                    "avatar",
                    "subdomain",
                )
            },
        ),
        (
            "Affiliate Commission",
            {
                "classes": ("wide",),
                "fields": (
                    "affiliate_commission",
                    "total_pending_commissions",
                    "total_coin_pending_commissions",
                ),
            },
        ),
        (
            "Stripe Connection",
            {
                "classes": ("collapse",),
                "fields": (
                    "stripe_onboarding",
                    "stripe_account_id",
                ),
            },
        ),
        (
            "Coinpayment Connection",
            {
                "classes": ("collapse",),
                "fields": (
                    "coinpayment_onboarding",
                    "coinpayment_api_secret_key",
                    "coinpayment_api_public_key",
                ),
            },
        ),
    )

    def get_inlines(self, request, obj=None):
        """
        Returns a list of inline classes to be displayed in the admin change form.

        Args:
            request (HttpRequest): The HTTP request object.
            obj (YourModel): The instance of the model being edited.

        Returns:
            list of InlineModelAdmin: A list of inline classes based on conditions.
        """
        if obj and obj.stripe_onboarding:
            return [ServerInline, StripePlanInline]
        elif obj and obj.coinpayment_onboarding:
            return [ServerInline, CoinPlanInline]

    def get_all_model_fields(self, model):
        """
        Retrieves all field names of a given model dynamically.

        Args:
            model (Model): The Django model for which field names are to be retrieved.

        Returns:
            list of str: A list of field names of the specified model.
        """
        return [field.name for field in model._meta.get_fields()]

    def get_readonly_fields(self, request, obj=None):
        """
        Overrides the get_readonly_fields method to make all fields read-only.

        Args:
            request (HttpRequest): The HTTP request object.
            obj (YourModel): The instance of the model being edited.

        Returns:
            list of str: A list of field names that should be read-only.
        """
        return self.get_all_model_fields(self.model)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    """Admin class for managing Subscriber instances."""

    list_display = ["username", "email", "subscribed_via"]
    readonly_fields = [
        "user",
        "username",
        "email",
        "subscribed_via",
        "stripe_customer_id",
        "avatar",
        "discord_id",
    ]
    search_fields = ["username", "email"]
    search_help_text = "Search by username or email"
    view_on_site = False


@admin.register(CoinSubscription)
class CoinSubscriptionAdmin(admin.ModelAdmin):
    """Admin class for managing CoinSubscription instances."""

    list_display = ["subscriber", "plan", "subscription_date", "expiration_date", "coin_amount", "status"]
    list_filter = ["status"]


@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    """Admin class for managing StripeSubscription instances."""

    list_display = ["subscriber", "subscribed_via", "plan", "subscription_date", "expiration_date", "status"]
    search_fields = ["subscriber", "subscribed_via", "plan"]
    list_filter = ["status", "subscription_date", "expiration_date"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin class for managing User instances."""

    list_display = ["username", "is_serverowner", "is_affiliate", "is_subscriber", "is_superuser", "is_active"]
    readonly_fields = ["password"]


class PaymentDetailInline(admin.TabularInline):
    """Inline admin class for managing PaymentDetail instances within the Affiliate admin."""

    model = PaymentDetail
    extra = 0
    readonly_fields = ["litecoin_address", "body"]

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete PaymentDetail instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new PaymentDetail instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


class AffiliatePaymentInline(admin.TabularInline):
    """Inline admin class for managing AffiliatePayment instances within the Affiliate admin."""

    model = AffiliatePayment
    extra = 0
    readonly_fields = ["serverowner", "subscriber", "amount", "coin_amount", "paid", "date_payment_confirmed"]

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete AffiliatePayment instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new AffiliatePayment instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


class AffiliateInviteeInline(admin.TabularInline):
    """Inline admin class for managing AffiliateInvitee instances within the Affiliate admin."""

    model = AffiliateInvitee
    extra = 0
    readonly_fields = ["invitee_discord_id"]

    def has_delete_permission(self, request, obj=None):
        """Determine whether the user has permission to delete AffiliateInvitee instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False

    def has_add_permission(self, request, obj=None):
        """Determine whether the user has permission to add new AffiliateInvitee instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    """Admin class for managing Affiliate instances."""

    list_display = ["subscriber", "affiliate_link", "total_commissions_paid", "last_payment_date"]
    readonly_fields = [
        "subscriber",
        "affiliate_link",
        "discord_id",
        "server_id",
        "serverowner",
        "last_payment_date",
        "total_commissions_paid",
        "total_coin_commissions_paid",
        "pending_commissions",
        "pending_coin_commissions",
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "subscriber",
                    "discord_id",
                    "affiliate_link",
                    "serverowner",
                    "server_id",
                )
            },
        ),
        (
            "Commission Earnings",
            {
                "classes": ("wide",),
                "fields": (
                    "pending_commissions",
                    "total_commissions_paid",
                    "pending_coin_commissions",
                    "total_coin_commissions_paid",
                    "last_payment_date",
                ),
            },
        ),
    )
    view_on_site = False
    inlines = [PaymentDetailInline, AffiliatePaymentInline, AffiliateInviteeInline]


admin.site.unregister(Group)
