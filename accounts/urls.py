from django.urls import path

from . import views, webhooks

urlpatterns = [
    # Subscriber URLs
    path("subscriber/", views.subscriber_dashboard, name="subscriber_dashboard"),
    path(
        "subscribe/<int:product_id>/", views.subscribe_to_plan, name="subscribe_to_plan"
    ),
    path(
        "subscription/success/", views.subscription_success, name="subscription_success"
    ),
    # Affiliate URLs
    path("affiliate/", views.affiliate_dashboard, name="affiliate_dashboard"),
    path("affiliate/upgrade/", views.upgrade_to_affiliate, name="upgrade_to_affiliate"),
    path("affiliate/payments/", views.affiliate_payments, name="affiliate_payments"),
    path("affiliate/invitees/", views.affiliate_invitees, name="affiliate_invitees"),
    # Server Owner URLs
    path("serverowner/", views.dashboard, name="dashboard"),
    path("serverowner/plans/", views.plans, name="plans"),
    path("serverowner/plan/<int:product_id>/", views.plan_detail, name="plan"),
    path("serverowner/plan/deactivate/", views.deactivate_plan, name="deactivate_plan"),
    path("serverowner/subscribers/", views.subscribers, name="subscribers"),
    path(
        "serverowner/subscriber/<int:id>/",
        views.subscriber_detail,
        name="subscriber_detail",
    ),
    path("serverowner/affiliates/", views.affiliates, name="affiliates"),
    path(
        "serverowner/affiliates/payments/pending/",
        views.pending_affiliate_payment,
        name="pending_affiliate_payment",
    ),
    path(
        "serverowner/affiliates/payments/confirmed/",
        views.confirmed_affiliate_payment,
        name="confirmed_affiliate_payment",
    ),
    # Onboarding URLs
    path("onboarding/", views.onboarding, name="onboarding"),
    path(
        "create-stripe-account/",
        views.create_stripe_account,
        name="create_stripe_account",
    ),
    path("subscribe/", views.subscribe_redirect, name="subscribe_redirect"),
    path("collect-user-info/", views.collect_user_info, name="collect_user_info"),
    path("stripe-refresh/", views.stripe_refresh, name="stripe_refresh"),
    # General URLs
    path("webhook/", webhooks.stripe_webhook, name="stripe_webhook"),
    path("dashboard/", views.dashboard_view, name="dashboard_view"),
    path("delete-account/", views.delete_account, name="delete_account"),
    path("", views.index, name="index"),
]
