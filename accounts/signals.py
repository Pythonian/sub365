from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ServerOwner, Subscriber, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.is_serverowner:
            ServerOwner.objects.create(user=instance)
        if instance.is_subscriber:
            Subscriber.objects.create(user=instance)
