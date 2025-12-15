from django.contrib.auth.backends import ModelBackend

class PatientAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        if user and request.path == '/login/' and user.is_staff:
            return None  # Block staff from patient login
        return user