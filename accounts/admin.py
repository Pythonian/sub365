from django.contrib import admin
from django.contrib.auth.models import Group

from allauth.account.models import EmailAddress

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
    Subscriber,
    Subscription,
    User,
)


@admin.register(AccessCode)
class AccessCode(admin.ModelAdmin):
    """
    Admin class for managing AccessCode instances.
    """

    list_display = ["code", "used_by", "is_used", "date_used"]
    list_filter = ["is_used"]


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    """
    Admin class for managing Server instances.
    """

    list_display = ["name", "owner", "server_id", "choice_server"]
    list_filter = ["choice_server"]


@admin.register(ServerOwner)
class ServerOwnerAdmin(admin.ModelAdmin):
    """
    Admin class for managing ServerOwner instances.
    """

    list_display = [
        "username",
        "subdomain",
        "email",
        "affiliate_commission",
    ]
    search_fields = ["username", "subdomain", "email"]


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    """
    Admin class for managing Subscriber instances.
    """

    list_display = ["username", "email", "subscribed_via"]


@admin.register(StripePlan)
class StripePlanAdmin(admin.ModelAdmin):
    """
    Admin class for managing StripePlan instances.
    """

    list_display = ["name", "user", "amount", "subscriber_count"]
    search_fields = ["user__username"]


@admin.register(CoinPlan)
class CoinPlanAdmin(admin.ModelAdmin):
    """
    Admin class for managing CoinPlan instances.
    """
    
    list_display = ["name", "serverowner", "amount", "subscriber_count"]
    search_fields = ["serverowner__username"]


@admin.register(CoinSubscription)
class CoinSubscriptionAdmin(admin.ModelAdmin):
    """
    Admin class for managing CoinSubscription instances.
    """

    list_display = ["subscriber", "plan", "subscription_date", "expiration_date",
                    "coin_amount", "status"]
    list_filter = ["status"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Admin class for managing Subscription instances.
    """

    list_display = [
        "subscriber",
        "subscribed_via",
        "plan",
        "subscription_date",
        "expiration_date",
        "status",
    ]
    search_fields = ["subscriber", "subscribed_via", "plan"]
    list_filter = ["status", "subscription_date", "expiration_date"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Admin class for managing User instances.
    """

    list_display = [
        "username",
        "is_serverowner",
        "is_affiliate",
        "is_subscriber",
        "is_superuser",
        "is_active",
    ]


class PaymentDetailInline(admin.TabularInline):
    """
    Inline admin class for managing PaymentDetail instances within the Affiliate admin.    
    """
    model = PaymentDetail
    extra = 0
    readonly_fields = ["litecoin_address", "body"]

    def has_delete_permission(self, request, obj=None):
        """
        Determine whether the user has permission to delete PaymentDetail instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False
    

class AffiliatePaymentInline(admin.TabularInline):
    """
    Inline admin class for managing AffiliatePayment instances within the Affiliate admin.
    """
    model = AffiliatePayment
    extra = 0
    readonly_fields = ["serverowner", "subscriber", "amount", "coin_amount", "paid", 
                       "date_payment_confirmed"]
    
    def has_delete_permission(self, request, obj=None):
        """
        Determine whether the user has permission to delete AffiliatePayment instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to delete, False otherwise.
        """
        return False
    
    def has_add_permission(self, request, obj=None):
        """
        Determine whether the user has permission to add new AffiliatePayment instances.

        Args:
            request: The current request.
            obj (optional): The object being edited.

        Returns:
            bool: True if the user has permission to add, False otherwise.
        """
        return False


@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    """
    Admin class for managing Affiliate instances.
    """

    list_display = ["subscriber", "affiliate_link", "total_commissions_paid", "last_payment_date"]
    readonly_fields = ["subscriber", "affiliate_link", "discord_id", "server_id",
                       "serverowner", "last_payment_date", "total_commissions_paid",
                       "total_coin_commissions_paid", "pending_commissions", "pending_coin_commissions"]
    inlines = [PaymentDetailInline, AffiliatePaymentInline]


@admin.register(AffiliateInvitee)
class AffiliateInviteeAdmin(admin.ModelAdmin):
    """
    Admin class for managing AffiliateInvitee instances.
    """

    list_display = ["affiliate", "invitee_discord_id", "created"]


admin.site.unregister(EmailAddress)
admin.site.unregister(Group)
