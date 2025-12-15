from django import forms
from .models import Feedback, Response, Notification
from .widgets import MultiFileInput
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
import os

class FeedbackForm(forms.ModelForm):
    # Remove attachments from the form entirely since we handle it manually
    class Meta:
        model = Feedback
        fields = ['category', 'content', 'rating']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': _('Describe your feedback...')
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.HiddenInput()
        }
    
class ResponseForm(forms.ModelForm):
    class Meta:
        model = Response
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write your response here...'
            }),
        }

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 2}),
        }