from django.contrib import admin

from .models import User, ServerOwner, Server, StripePlan, Subscriber

admin.site.register([User, ServerOwner, Server, StripePlan, Subscriber])