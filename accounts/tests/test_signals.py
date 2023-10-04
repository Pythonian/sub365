from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import ServerOwner, Subscriber
from accounts.signals import create_user_profile

User = get_user_model()


class SignalReceiverTest(TestCase):
    def test_create_user_profile_serverowner(self):
        # Create a User instance with is_serverowner=True
        user = User.objects.create(username="pythonian", is_serverowner=True)

        # Emit the post_save signal for the User instance
        create_user_profile(sender=User, instance=user, created=True)

        # Check if a ServerOwner profile was created for the user
        self.assertTrue(ServerOwner.objects.filter(user=user).exists())

    def test_create_user_profile_subscriber(self):
        # Create a User instance with is_subscriber=True
        user = User.objects.create(username="pythonian", is_subscriber=True)

        # Emit the post_save signal for the User instance
        create_user_profile(sender=User, instance=user, created=True)

        # Check if a Subscriber profile was created for the user
        self.assertTrue(Subscriber.objects.filter(user=user).exists())

    def test_create_user_profile_existing_user(self):
        # Create a User instance with is_serverowner=True
        user = User.objects.create(username="pythonian")

        # Emit the post_save signal for the User instance with created=False
        create_user_profile(sender=User, instance=user, created=False)

        # Check that no new profile was created
        self.assertFalse(ServerOwner.objects.filter(user=user).exists())
        self.assertFalse(Subscriber.objects.filter(user=user).exists())
