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

admin.site.site_header = 'SUB365 Admin'
admin.site.index_title = 'SUB365 Admin'
admin.site.site_title = 'SUB365 Administration'

handler500 = 'accounts.views.error_500'
handler404 = 'accounts.views.error_404'
handler400 = 'accounts.views.error_400'
handler403 = 'accounts.views.error_403'
