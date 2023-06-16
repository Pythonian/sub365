from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        #TODO Use reverse('discord_callback')
        return '/accounts/discord/login/callback/'
