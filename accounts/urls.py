from django.urls import path

from . import views, webhooks

urlpatterns = [
    path("subscribe/", views.subscribe_redirect, name="subscribe_redirect"),
    path("choosename/", views.choose_name, name="choose_name"),
    path("dashboard_view/", views.dashboard_view, name="dashboard_view"),
    path("create-stripe-account/", views.create_stripe_account, name="create_stripe_account"),
    path("collect-user-info/", views.collect_user_info, name="collect_user_info"),
    path("stripe-refresh/", views.stripe_refresh, name="stripe_refresh"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("plans/", views.plans, name="plans"),
    path("plan/<int:product_id>/", views.plan_detail, name="plan"),
    path("deactivate_plan/", views.deactivate_plan, name="deactivate_plan"),
    path("subscribers/", views.subscribers, name="subscribers"),
    path("mysubscriber/<int:id>/", views.subscriber_detail, name="subscriber_detail"),
    path("affiliates/", views.affiliates, name="affiliates"),
    path("subscriber/", views.subscriber_dashboard, name="subscriber_dashboard"),
    path("subscribe/<int:product_id>/", views.subscribe_to_plan, name="subscribe_to_plan"),
    path("subscription/success/", views.subscription_success, name="subscription_success"),
    path("become-affiliate/", views.upgrade_to_affiliate, name="upgrade_to_affiliate"),
    path("affiliate/", views.affiliate_dashboard, name="affiliate_dashboard"),
    path("affiliate/invitations/", views.affiliate_invitations, name="affiliate_invitations"),
    path('webhook/', webhooks.stripe_webhook, name='stripe_webhook'),
    path("", views.index, name="index"),
]
