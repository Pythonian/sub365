from django.urls import reverse

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class DiscordAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for handling login redirect URLs.
    """

    def get_login_redirect_url(self, request):
        """
        Return the redirect URL for successful social account login.

        :param request: The current request object.
        :return: The redirect URL.
        """
        return reverse("discord_callback")
