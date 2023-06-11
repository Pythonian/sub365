from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import discord_callback

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/discord/login/callback/', discord_callback, name='discord_callback'),
    path('accounts/', include('allauth.urls')),
    path('', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
