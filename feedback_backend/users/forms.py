from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile
import vonage
import re
import logging
from django.urls import reverse
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class VonageSMSService:
    """Production-grade SMS service with rate limiting and validation"""
    
    def __init__(self):
        if not all([settings.VONAGE_API_KEY, settings.VONAGE_API_SECRET]):
            logger.error("Vonage credentials not configured")
            raise ValueError("Vonage credentials not properly configured")
        
        self.client = vonage.Client(
            key=settings.VONAGE_API_KEY,
            secret=settings.VONAGE_API_SECRET
        )
        self.sms = vonage.Sms(self.client)
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS with rate limiting and validation"""
        try:
            # Rate limiting check
            cache_key = f"sms_rate_limit:{phone_number}"
            if cache.get(cache_key):
                logger.warning(f"Rate limit exceeded for {phone_number}")
                return False
                
            # Validate and normalize phone number
            normalized_phone = self._normalize_phone(phone_number)
            if not normalized_phone:
                raise ValidationError(_("Invalid phone number format"))

            # Send message
            response = self.sms.send_message({
                'from': settings.VONAGE_SENDER_ID,
                'to': normalized_phone,
                'text': message[:1600]  # Truncate to 1600 chars
            })
            
            if response['messages'][0]['status'] == '0':
                cache.set(cache_key, True, timeout=300)  # 5 min rate limit
                logger.info(f"SMS sent to {phone_number}")
                return True
                
            error = response['messages'][0]['error-text']
            logger.error(f"Vonage SMS failed: {error}")
            return False
            
        except Exception as e:
            logger.error(f"SMS sending error: {str(e)}")
            return False
    
    def _normalize_phone(self, phone_number: str) -> str:
        """Convert phone number to E.164 format"""
        cleaned = re.sub(r'[^0-9+]', '', phone_number)
        if not re.match(r'^\+[1-9]\d{9,14}$', cleaned):
            return None
        return cleaned


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
            'placeholder': _('your@email.com')
        }),
        help_text=_("We'll never share your email with anyone else.")
    )
    
    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=17,
        validators=[RegexValidator(
            regex=r'^\+[1-9]\d{9,14}$',
            message=_("Enter a valid international phone number with country code (e.g. +255123456789).")
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('+255123456789')
        }),
        help_text=_("Include country code for SMS notifications.")
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'phone_number', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('username')
            }),
        }
        help_texts = {
            'username': _('150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError(
                _("This email is already registered."),
                code='email_exists'
            )
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if Profile.objects.filter(phone_number=phone_number).exists():
            raise ValidationError(
                _("This phone number is already in use."),
                code='phone_exists'
            )
        return phone_number

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$', password1):
            raise ValidationError(
                _("Password must contain at least one letter and one number."),
                code='password_invalid'
            )
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = Profile.objects.create(
                user=user,
                phone_number=self.cleaned_data['phone_number']
            )
            self._send_welcome_notifications(user, profile)
        return user

    def _send_welcome_notifications(self, user, profile):
        """Handles all post-registration notifications"""
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL
        }

        # Initialize counters
        email_sent, sms_sent = False, False

        # Email Notification
        if profile.notification_preference in ['Email', 'Both']:
            email_sent = self._send_welcome_email(user, context)

        # SMS Notification
        if profile.notification_preference in ['SMS', 'Both']:
            sms_sent = self._send_welcome_sms(profile.phone_number, context)

        # If both notification methods failed
        if not email_sent and not sms_sent:
            raise ValidationError(
                _("We couldn't send your welcome notifications. Please contact support."),
                code='notifications_failed'
            )

    def _send_welcome_email(self, user, context):
        """Send welcome email with error handling"""
        try:
            send_mail(
                subject=_("Welcome to %(site_name)s") % {'site_name': settings.SITE_NAME},
                message=render_to_string('users/emails/welcome_email.txt', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=render_to_string('users/emails/welcome_email.html', context),
                fail_silently=False
            )
            logger.info(f"Sent welcome email to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Email failed to {user.email}: {str(e)}")
            return False

    def _send_welcome_sms(self, phone_number, context):
        """Send welcome SMS with error handling"""
        try:
            sms_service = VonageSMSService()
            message = render_to_string('users/sms/welcome_sms.txt', context)
            if sms_service.send_sms(phone_number, message):
                return True
            return False
        except Exception as e:
            logger.error(f"SMS failed to {phone_number}: {str(e)}")
            return False


class PatientLoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("Email or Username"),
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'class': 'form-control',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control'
        })
    )

    error_messages = {
        'invalid_login': _("Please enter a correct email/username and password."),
        'inactive': _("This account is inactive."),
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

class ProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'},
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d'],
        required=False
    )
    
    phone_number = forms.CharField(
        validators=[RegexValidator(
            regex=r'^\+[1-9]\d{9,14}$',
            message=_("Enter a valid international phone number with country code.")
        )],
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = Profile
        fields = ['phone_number', 'profile_picture', 'bio', 'date_of_birth', 'notification_preference']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Tell us about yourself...')
            }),
            'notification_preference': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'profile_picture': _('Profile Image'),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob.year < 1930:
            raise ValidationError(
                _("Please enter a valid birth year."),
                code='invalid_birth_year'
            )
        return dob

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and Profile.objects.exclude(user=self.instance.user).filter(phone_number=phone_number).exists():
            raise ValidationError(
                _("This phone number is already in use."),
                code='phone_exists'
            )
        return phone_number

class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['dark_mode', 'font_size', 'preferred_language', 'notification_preference']
        widgets = {
            'font_size': forms.Select(attrs={'class': 'form-select'}),
            'preferred_language': forms.Select(attrs={'class': 'form-select'}),
            'dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_preference': forms.Select(attrs={'class': 'form-select'}),
        }