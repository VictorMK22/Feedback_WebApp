from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Controls whether regular signups are allowed.
        """
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
    
    def get_login_redirect_url(self, request):
        """
        Customize where users are redirected after login.
        """
        if request.user.is_authenticated and request.user.is_staff:
            return reverse('admin:index')
        return super().get_login_redirect_url(request) or settings.LOGIN_REDIRECT_URL
    
    def save_user(self, request, user, form, commit=True):
        """
        Custom user saving logic.
        """
        user = super().save_user(request, user, form, commit=False)
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        """
        Controls whether social signups are allowed.
        """
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)
    
    def pre_social_login(self, request, sociallogin):
        """
        Custom logic before social login completes.
        """
        super().pre_social_login(request, sociallogin)
        # Add any pre-login hooks here
    
    def populate_user(self, request, sociallogin, data):
        """
        Customize how user data is populated from social providers.
        """
        user = super().populate_user(request, sociallogin, data)
        user.username = data.get('email', '')  # Use email as username
        return user