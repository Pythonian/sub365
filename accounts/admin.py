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
    list_display = ["code", "used_by", "is_used"]
    list_filter = ["is_used"]


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "server_id", "choice_server"]
    list_filter = ["choice_server"]


@admin.register(ServerOwner)
class ServerOwnerAdmin(admin.ModelAdmin):
    list_display = [
        "username",
        "subdomain",
        "email",
        "affiliate_commission",
        "coinbase_onboarding",
    ]
    search_fields = ["username", "subdomain", "email"]


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "subscribed_via"]


@admin.register(StripePlan)
class StripePlanAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "amount", "subscriber_count"]
    search_fields = ["user__username"]


@admin.register(CoinPlan)
class CoinPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "serverowner", "amount", "subscriber_count"]
    search_fields = ["serverowner__username"]


@admin.register(CoinSubscription)
class CoinSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["subscriber", "plan", "subscription_date", "expiration_date",
                    "coin_amount", "status"]
    list_filter = ["status"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
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
    list_display = [
        "username",
        "is_serverowner",
        "is_affiliate",
        "is_subscriber",
        "is_superuser",
        "is_active",
    ]


class PaymentDetailInline(admin.StackedInline):
    model = PaymentDetail
    extra = 0


@admin.register(Affiliate)
class AffiliateAdmin(admin.ModelAdmin):
    list_display = ["subscriber", "affiliate_link", "created"]
    inlines = [PaymentDetailInline]


@admin.register(AffiliateInvitee)
class AffiliateInviteeAdmin(admin.ModelAdmin):
    list_display = ["affiliate", "invitee_discord_id", "created"]


@admin.register(AffiliatePayment)
class AffiliatePaymentAdmin(admin.ModelAdmin):
    list_display = ["serverowner", "affiliate", "subscriber",
                    "amount", "coin_amount", "paid"]


admin.site.unregister(EmailAddress)
admin.site.unregister(Group)
