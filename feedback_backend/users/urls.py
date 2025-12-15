from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    register_view,
    patient_login_view,
    logout_view,
    reset_password_request,
    profile_view,
    # save_settings,
    get_user_settings,
    save_user_settings
)

app_name = "users"

urlpatterns = [
    # Authentication endpoints
    path('register/', register_view, name='register'),
    path('login/', patient_login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Profile endpoint
    path('profile/', profile_view, name='profile'),
    
    # Password Reset URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset.html',
             email_template_name='users/password_reset_email.html',
             subject_template_name='users/password_reset_subject.txt',
             success_url=reverse_lazy('users:password_reset_done'),
             html_email_template_name='users/password_reset_email.html',
         ),
         name='password_reset'),
    
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='users/password_reset_sent.html'
         ),
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='users/password_reset_confirm.html',
             success_url=reverse_lazy('users:password_reset_complete'),
         ),
         name='password_reset_confirm'),
    
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='users/password_reset_complete.html'
         ),
         name='password_reset_complete'),
    
    # Custom password reset landing page
    path('reset-password/', reset_password_request, name='reset_password_request'),


    # # path('settings/save/', save_settings, name='save_settings'),
    path('api/get-settings/', get_user_settings, name='get_user_settings'),
    path('api/save-settings/', save_user_settings, name='save_user_settings'),
]