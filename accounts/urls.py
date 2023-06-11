from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('choosename/', views.choose_name, name='choose_name'),
    path('stripe-refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('create_stripe_account/', views.create_stripe_account, name='create_stripe_account'),
    path('collect_user_info/', views.collect_user_info, name='collect_user_info'),
    path('create_plan/', views.create_plan, name='create_plan'),
    path('delete_plan/', views.delete_plan, name='delete_plan'),
    path('<str:subdomain>/subscriptions/', views.list_plans, name='list_plans'),
    path('plans/subscribe/<int:plan_id>/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('plans/subscribe/success/', views.subscribe_success, name='subscribe_success'),
    path('plans/subscribe/cancel/', views.subscribe_cancel, name='subscribe_cancel'),
    # path('subscriber_auth/<str:subdomain>/', views.subscriber_auth, name='subscriber_auth'),
    # path('subscriber-callback/<str:subdomain>/', views.subscriber_callback, name='subscriber_callback'),
    # path('<str:subdomain>/subscribe/', views.subscriber_plans, name='subscriber_plans'),
    path('', views.landing_page, name='landing_page'),
]
