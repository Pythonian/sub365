from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.test import TestCase

User = get_user_model()


class OnboardingCompletedDecoratorTest(TestCase):
    def setUp(self):
        # Create a user and a related ServerOwner object for testing
        self.user = User.objects.create_user(
            username="test_user",
            password="test_password",
            is_serverowner=True,
            discord_id="test_discord_id",
        )
        # Create a related ServerOwner object for testing
        self.serverowner = self.user

    def test_onboarding_completed_with_missing_subdomain(self):
        # Simulate a user with a missing subdomain
        self.serverowner.subdomain = ""
        self.serverowner.save()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("onboarding"))

    def test_onboarding_completed_with_stripe_not_completed(self):
        # Simulate a user with stripe onboarding not completed
        self.serverowner.stripe_account_id = "test_stripe_account_id"
        self.serverowner.stripe_onboarding = False
        self.serverowner.save()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("collect_user_info"))

    def test_onboarding_completed_with_stripe_and_missing_coinpayment_keys(self):
        # Simulate a user with stripe onboarding completed but missing coinpayment keys
        self.serverowner.stripe_onboarding = True
        self.serverowner.coinpayment_api_public_key = ""
        self.serverowner.coinpayment_api_secret_key = ""
        self.serverowner.save()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)  # Should continue to the decorated view

    def test_onboarding_completed_with_missing_coinpayment_keys(self):
        # Simulate a user with missing coinpayment keys
        self.serverowner.stripe_onboarding = True
        self.serverowner.coinpayment_api_public_key = ""
        self.serverowner.coinpayment_api_secret_key = ""
        self.serverowner.save()
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("onboarding_crypto"))

    def test_onboarding_completed_with_nonexistent_serverowner(self):
        # Simulate a user without a ServerOwner object
        self.user.serverowner.delete()  # Delete the related ServerOwner object
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("index"))
