from django.test import TestCase

from ..models import ServerOwner, Subscriber, User
from ..signals import create_user_profile


class SignalReceiverTest(TestCase):
    """Test case for signal receivers."""

    def test_create_user_profile_serverowner(self):
        """Test creation of a ServerOwner profile."""
        # Create a User instance with is_serverowner=True
        user = User.objects.create(username="pythonian", is_serverowner=True)

        # Emit the post_save signal for the User instance
        create_user_profile(sender=User, instance=user, created=True)

        # Check if a ServerOwner profile was created for the user
        assert ServerOwner.objects.filter(user=user).exists()

    def test_create_user_profile_subscriber(self):
        """Test creation of a Subscriber profile."""
        # Create a User instance with is_subscriber=True
        user = User.objects.create(username="pythonian", is_subscriber=True)

        # Emit the post_save signal for the User instance
        create_user_profile(sender=User, instance=user, created=True)

        # Check if a Subscriber profile was created for the user
        assert Subscriber.objects.filter(user=user).exists()

    def test_create_user_profile_existing_user(self):
        """Test handling of an existing user."""
        # Create a User instance with is_serverowner=True
        user = User.objects.create(username="pythonian")

        # Emit the post_save signal for the User instance with created=False
        create_user_profile(sender=User, instance=user, created=False)

        # Check that no new profile was created
        assert not ServerOwner.objects.filter(user=user).exists()
        assert not Subscriber.objects.filter(user=user).exists()
