from django.urls import path

from . import views

urlpatterns = [
    path('subscribe/', views.subscribe_redirect, name='subscribe_redirect'),
    path('choosename/', views.choose_name, name='choose_name'),
    path('dashboard_view/', views.dashboard_view, name='dashboard_view'),
    path('create_stripe_account/', views.create_stripe_account, name='create_stripe_account'),
    path('collect_user_info/', views.collect_user_info, name='collect_user_info'),
    path('stripe-refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('plans/', views.plans, name='plans'),
    path('plan/<int:product_id>/', views.plan_detail, name='plan'),
    path('delete_plan/', views.delete_plan, name='delete_plan'),
    path('subscribers/', views.subscribers, name='subscribers'),
    path('subscriber/', views.subscriber_dashboard, name='subscriber_dashboard'),
    path('subscribe/<int:product_id>/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('', views.index, name='index'),
]
