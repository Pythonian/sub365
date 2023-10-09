from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls),
    path("feedback/", include("feedback.urls")),
    path("", include("accounts.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "SUB365 Admin"
admin.site.index_title = "SUB365 Admin"
admin.site.site_title = "SUB365 Administration"

handler404 = "accounts.views.error_404"
handler400 = "accounts.views.error_400"
handler403 = "accounts.views.error_403"
handler405 = "accounts.views.error_405"
handler500 = "accounts.views.error_500"
