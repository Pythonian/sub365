from django.contrib import admin

from .models import Profile, StripePlan, Server

admin.site.register([Profile, StripePlan, Server])