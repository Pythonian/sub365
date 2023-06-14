from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('plans/', views.plans, name='plans'),
    path('subscribers/', views.subscribers, name='subscribers'),
    path('choosename/', views.choose_name, name='choose_name'),
    path('stripe-refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('create_stripe_account/', views.create_stripe_account, name='create_stripe_account'),
    path('collect_user_info/', views.collect_user_info, name='collect_user_info'),
    path('create_plan/', views.create_plan, name='create_plan'),
    path('plan/<int:plan_id>/', views.plan_detail, name='plan'),
    path('delete_plan/', views.delete_plan, name='delete_plan'),
    # path('<str:subdomain>/subscriptions/', views.list_plans, name='list_plans'),
    path('plans/subscribe/<int:plan_id>/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('subscriber/', views.subscriber_dashboard, name='subscriber_dashboard'),
    path('plans/subscribe/cancel/', views.subscribe_cancel, name='subscribe_cancel'),
    path('subscribe/', views.subscribe_redirect, name='subscribe_redirect'),
    path('<str:subdomain>/subscriptions/', views.subscriber_plans, name='subscriber_plans'),
    path('cancel_subscription/<int:subscription_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('dashboard_view/', views.dashboard_view, name='dashboard_view'),
    path('', views.index, name='index'),
]
