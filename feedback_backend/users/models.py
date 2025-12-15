from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import os

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username=None, password=None, **extra_fields):
        """
        Creates and saves a user with the given email and password.
        """
        if not email:
            raise ValueError(_('Users must have an email address'))
        
        email = self.normalize_email(email)
        
        # Generate username from email if not provided
        if not username:
            base_username = email.split('@')[0]
            username = self.generate_unique_username(base_username)
        
        user = self.model(
            email=email,
            username=username,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_social_user(self, email, username=None, auth_provider=None, **extra_fields):
        """
        Creates a user authenticated via social provider.
        """
        if not email:
            raise ValueError(_('Social auth users must have an email address'))
        
        email = self.normalize_email(email)
        
        if not username:
            base_username = email.split('@')[0]
            username = self.generate_unique_username(base_username)
        
        if not auth_provider:
            raise ValueError(_('Social auth provider must be specified'))
        
        user = self.model(
            email=email,
            username=username,
            auth_provider=auth_provider,
            is_verified=True,
            **extra_fields
        )
        user.set_unusable_password()
        user.save(using=self._db)
        Profile.objects.get_or_create(user=user)
        return user

    def create_superuser(self, email, username=None, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', CustomUser.Role.ADMIN)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, username, password, **extra_fields)

    def generate_unique_username(self, base_username):
        """
        Generates a unique username by appending numbers if needed.
        """
        username = base_username
        counter = 1
        while self.model.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'Patient', _('Patient')
        ADMIN = 'Admin', _('Admin')
    
    class AuthProvider(models.TextChoices):
        EMAIL = 'email', _('Email')
        FACEBOOK = 'facebook', _('Facebook')
        GOOGLE = 'google', _('Google')
    
    # Remove original username field to redefine with different attributes
    username = None
    
    # Core fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _('A user with that email already exists.'),
        }
    )
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Optional. If not provided, will be generated from email.'),
        error_messages={
            'unique': _('A user with that username already exists.'),
        }
    )
    
    # Role and authentication
    role = models.CharField(
        _('role'),
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT
    )
    auth_provider = models.CharField(
        _('auth provider'),
        max_length=10,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL
    )
    
    # Social auth fields
    facebook_id = models.CharField(
        _('facebook ID'),
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    google_id = models.CharField(
        _('google ID'),
        max_length=100,
        blank=True,
        null=True,
        unique=True
    )
    
    # Verification and preferences
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Designates whether the user has verified their email.')
    )
    preferred_language = models.CharField(
        _('preferred language'),
        max_length=10,
        default='en',
        choices=[
            ('en', _('English')),
            ('sw', _('Swahili')),
            ('es', _('Spanish')),
            ('fr', _('French')),
            ('de', _('German')),
        ]
    )
    
    # Security fields
    last_password_change = models.DateTimeField(
        _('last password change'),
        auto_now_add=True
    )
    
    # Meta
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self._validate_social_ids()
        
    def _validate_social_ids(self):
        """Ensure social IDs are only set when using that auth provider."""
        social_fields = {
            'facebook': self.facebook_id,
            'google': self.google_id,
        }
        
        if self.auth_provider != 'email':
            if not social_fields.get(self.auth_provider):
                raise ValidationError(
                    _(f'{self.auth_provider} ID must be set when using {self.auth_provider} auth.')
                )


def profile_picture_upload_path(instance, filename):
    """Generate upload path for profile pictures."""
    ext = os.path.splitext(filename)[1]
    return f'profile_pictures/user_{instance.user.id}/profile{ext}'


class Profile(models.Model):
    class NotificationPreference(models.TextChoices):
        SMS = 'SMS', _('SMS')
        EMAIL = 'Email', _('Email')
        BOTH = 'Both', _('Both')
        NONE = 'None', _('None')
    
    class Gender(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    )
    phone_number = models.CharField(
        _('phone number'),
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        unique=True
    )
    secondary_email = models.EmailField(
        _('secondary email'),
        blank=True,
        null=True
    )
    
    # Personal Information
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to=profile_picture_upload_path,
        blank=True,
        null=True,
        max_length=500
    )
    bio = models.TextField(
        _('biography'),
        blank=True,
        null=True,
        max_length=500
    )
    date_of_birth = models.DateField(
        _('date of birth'),
        blank=True,
        null=True
    )
    gender = models.CharField(
        _('gender'),
        max_length=1,
        choices=Gender.choices,
        blank=True,
        null=True
    )
    
    # Preferences
    notification_preference = models.CharField(
        _('notification preference'),
        max_length=10,
        choices=NotificationPreference.choices,
        default=NotificationPreference.BOTH
    )

    dark_mode = models.BooleanField(
        _('dark mode'),
        default=False
    )
    font_size = models.CharField(
        _('font size'),
        max_length=10,
        choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')],
        default='medium'
    )
    preferred_language = models.CharField(
        _('preferred language'),
        max_length=5,
        choices=[('en', 'English'), ('sw', 'Swahili'), ('es', 'Spanish'), ('fr', 'French')],
        default='en'
    )
    
    # Add this method to get all settings
    def get_settings(self):
        return {
            'dark_mode': self.dark_mode,
            'font_size': self.font_size,
            'preferred_language': self.preferred_language,
            'notification_preference': self.notification_preference,
            # Include other relevant fields
        }
    
    # Metadata
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True
    )

    class Meta:
        verbose_name = _('profile')
        verbose_name_plural = _('profiles')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s Profile"

    def clean(self):
        super().clean()
        if self.date_of_birth and self.date_of_birth.year < 1930:
            raise ValidationError(
                {'date_of_birth': _('Please enter a valid birth year.')}
            )

    @property
    def age(self):
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )