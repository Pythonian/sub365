from django.contrib.auth.views import LogoutView
from django.urls import include, path

from . import views, webhooks

urlpatterns = [
    # Subscriber URLs
    path("subscriber/", views.subscriber_dashboard, name="subscriber_dashboard"),
    path("subscribe/<uuid:plan_id>/", views.subscribe_to_plan, name="subscribe_to_plan"),
    path("subscribe-to-coin/<uuid:plan_id>/", views.subscribe_to_coin_plan, name="subscribe_to_coin_plan"),
    path("subscription/success/", views.subscription_success, name="subscription_success"),
    path("subscription/cancel/", views.subscription_cancel, name="subscription_cancel"),
    # Affiliate URLs
    path(
        "affiliate/",
        include(
            [
                path("", views.affiliate_dashboard, name="affiliate_dashboard"),
                path("upgrade/", views.upgrade_to_affiliate, name="upgrade_to_affiliate"),
                path("payments/", views.affiliate_payments, name="affiliate_payments"),
                path("invitees/", views.affiliate_invitees, name="affiliate_invitees"),
            ],
        ),
    ),
    # Serverowner URLs
    path(
        "serverowner/",
        include(
            [
                path("", views.dashboard, name="dashboard"),
                path("plans/", views.plans, name="plans"),
                path("plan/<uuid:plan_id>/", views.plan_detail, name="plan_detail"),
                path("plan/deactivate/", views.deactivate_plan, name="deactivate_plan"),
                path("subscribers/", views.subscribers, name="subscribers"),
                path("subscriber/<uuid:subscriber_id>/", views.subscriber_detail, name="subscriber_detail"),
                path("affiliates/", views.affiliates, name="affiliates"),
                path("affiliate/<uuid:subscriber_id>/", views.affiliate_detail, name="affiliate_detail"),
                path(
                    "affiliates/payments/pending/", views.pending_affiliate_payment, name="pending_affiliate_payment"
                ),
                path(
                    "affiliates/payments/confirmed/",
                    views.confirmed_affiliate_payment,
                    name="confirmed_affiliate_payment",
                ),
            ],
        ),
    ),
    # Onboarding URLs
    path(
        "onboarding/",
        include(
            [
                path("", views.onboarding, name="onboarding"),
                path("coinpayment/", views.onboarding_crypto, name="onboarding_crypto"),
                path("stripe/", views.create_stripe_account, name="create_stripe_account"),
                path("stripe/userinfo/", views.collect_user_info, name="collect_user_info"),
                path("stripe/refresh/", views.stripe_refresh, name="stripe_refresh"),
            ],
        ),
    ),
    # Auth URLs
    path(
        "accounts/",
        include(
            [
                path("delete/", views.delete_account, name="delete_account"),
                path("discord/login/", views.discord_login, name="discord_login"),
                path("discord/login/callback/", views.discord_callback, name="discord_callback"),
                path("logout/", LogoutView.as_view(next_page="index"), name="accounts_logout"),
            ],
        ),
    ),
    # General URLs
    path("subscribe/", views.subscribe_redirect, name="subscribe_redirect"),
    path("webhook/", webhooks.stripe_webhook, name="stripe_webhook"),
    path("dashboard/", views.dashboard_view, name="dashboard_view"),
    path("check_pending_subscription", views.check_pending_subscription, name="check_pending_subscription"),
    path("", views.index, name="index"),
]
