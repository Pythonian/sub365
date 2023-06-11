from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    avatar = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.user.username
    
    def get_dashboard_url(self):
        return reverse('dashboard') + f'?so={self.subdomain}'


class StripePlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    plan_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    amount = models.IntegerField()
    currency = models.CharField(max_length=3)
    interval = models.CharField(max_length=10)

    def __str__(self):
        return self.name


class Server(models.Model):
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='servers')
    server_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    choice_server = models.BooleanField(default=False)

    def __str__(self):
        return self.name