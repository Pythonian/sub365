from django.urls import path

from . import views

urlpatterns = [
    path('accounts/discord/login/callback/', views.discord_callback, name='discord_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('choosename/', views.choose_name, name='choose_name'),
    path('stripe-refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('create_stripe_account/', views.create_stripe_account, name='create_stripe_account'),
    path('collect_user_info/', views.collect_user_info, name='collect_user_info'),
    path('create_plan/', views.create_plan, name='create_plan'),
    path('delete_plan/', views.delete_plan, name='delete_plan'),
    # path('subscriber_auth/<str:subdomain>/', views.subscriber_auth, name='subscriber_auth'),
    # path('subscriber-callback/<str:subdomain>/', views.subscriber_callback, name='subscriber_callback'),
    # path('<str:subdomain>/subscribe/', views.subscriber_plans, name='subscriber_plans'),
    path('', views.landing_page, name='index'),
]
