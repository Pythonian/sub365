"""Signal receiver function for handling user profile creation upon User model save."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ServerOwner, Subscriber, User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a user profile upon User model save.

    This function handles the creation of a user profile (either ServerOwner or Subscriber)
    when a new User instance is created.

    Args:
        sender (class): The sender class of the signal (User).
        instance (User): The instance of the User model that triggered the signal.
        created (bool): A boolean indicating whether the User instance was newly created.
        **kwargs: Additional keyword arguments passed to the function.

    Returns:
        None
    """
    if created:
        if instance.is_serverowner and not hasattr(instance, "serverowner"):
            # Create a ServerOwner profile for server owners
            ServerOwner.objects.create(user=instance)
        elif instance.is_subscriber and not hasattr(instance, "subscriber"):
            # Create a Subscriber profile for subscribers
            Subscriber.objects.create(user=instance)
