from django.urls import path

from . import views

urlpatterns = [
    path('accounts/discord/login/callback/', views.discord_callback, name='discord_callback'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.landing_page, name='index'),
]
