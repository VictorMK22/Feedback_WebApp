from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import PasswordResetView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from .forms import UserRegistrationForm, PatientLoginForm, ProfileForm
from .models import CustomUser, Profile
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, _('Registration successful! Please log in.'))
            return redirect('users:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

@csrf_protect
def patient_login_view(request):
    # Get next URL from GET or POST parameters
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('feedback:home-dashboard')
    
    if request.method == 'POST':
        form = PatientLoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # --- Safe redirect to next_url ---
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            # --- Role-based fallback ---
            if user.role == CustomUser.Role.ADMIN:
                return redirect('admin:index')

            # Default fallback for regular users
            return redirect('feedback:home-dashboard')

        # Invalid login → show error
        messages.error(request, _("Invalid username or password."))

    else:
        form = PatientLoginForm()

    # Render login page with form and next_url
    return render(request, 'users/login.html', {
        'form': form,
        'next': next_url,   # pass it to template
    })
    
def logout_view(request):
    logout(request)
    messages.success(request, _('You have been logged out.'))
    return redirect('users:login')

def reset_password_request(request):
    if request.method == 'POST':
        return PasswordResetView.as_view(
            template_name='users/password_reset.html',
            email_template_name='users/password_reset_email.html',
            subject_template_name='users/password_reset_subject.txt',
            success_url=reverse_lazy('users:password_reset_done')
        )(request)
    return render(request, 'users/password_reset_request.html')

@login_required
def profile_view(request):
    profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully!'))
            return redirect('feedback:home-dashboard')
        else:
            messages.error(request, _('Please correct the errors below.'))
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'users/profile.html', {
        'form': form,
        'profile': profile
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_settings(request):
    profile = request.user.profile
    data = {
        'dark_mode': profile.dark_mode,
        'font_size': profile.font_size or 'medium',
        'preferred_language': profile.preferred_language or 'en',
        'success': True
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_user_settings(request):
    profile = request.user.profile
    profile.dark_mode = request.data.get('dark_mode') == 'on'
    profile.font_size = request.data.get('font_size', 'medium')
    profile.preferred_language = request.data.get('preferred_language', 'en')
    profile.save()

    if request.user.preferred_language != profile.preferred_language:
        request.user.preferred_language = profile.preferred_language
        request.user.save()

    return Response({
        'success': True,
        'dark_mode': profile.dark_mode,
        'font_size': profile.font_size,
        'preferred_language': profile.preferred_language,
        'message': 'Settings saved successfully'
    })