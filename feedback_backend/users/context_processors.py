from django.conf import settings

def user_settings(request):
    if request.user.is_authenticated:
        profile = request.user.profile
        return {
            'user_settings': profile.get_settings()
        }
    return {}