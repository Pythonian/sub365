from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ServerOwner, Subscriber, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver function to create a user profile when a new user is created.
    """
    if created:
        if instance.is_serverowner:
            # Create a ServerOwner profile for server owners
            ServerOwner.objects.create(user=instance)
        if instance.is_subscriber:
            # Create a Subscriber profile for subscribers
            Subscriber.objects.create(user=instance)
