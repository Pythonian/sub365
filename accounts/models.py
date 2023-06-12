from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_serverowner = models.BooleanField(default=False)
    is_subscriber = models.BooleanField(default=False)


class ServerOwner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    subdomain = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.username
    

class Server(models.Model):
    owner = models.ForeignKey(ServerOwner, on_delete=models.CASCADE, related_name='servers')
    server_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    choice_server = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Subscriber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    discord_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField()
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.discord_id


class StripePlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    plan_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=3)
    interval = models.CharField(max_length=10)

    def __str__(self):
        return self.name
