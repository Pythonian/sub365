from django.contrib import admin

from .models import User, ServerOwner, Server, StripePlan, Subscriber, Subscription


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'server_id', 'choice_server']
    list_filter = ['choice_server']


@admin.register(ServerOwner)
class ServerOwnerAdmin(admin.ModelAdmin):
    list_display = ['username', 'subdomain', 'email']
    search_fields = ['username', 'subdomain', 'email']


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'subscribed_via']


@admin.register(StripePlan)
class StripePlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'amount']
    search_fields = ['user']

admin.site.register([User, Subscription])
