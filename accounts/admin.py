from django.contrib import admin

from .models import Profile, StripePlan

admin.site.register([Profile, StripePlan])