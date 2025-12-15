from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from users.views import patient_login_view

urlpatterns = [
    # Home dashboard (now included via feedback app)
    path('', include('feedback.urls'), name="feedback"),
    
    # Admin Interface
    path('admin/', admin.site.urls),

    # User Management
    path('users/', include('users.urls'), name="users"),

    # Reports Management
    path('reports/', include('reports.urls')),

    # # Alias for accounts/login → same view as users/login
    # path('accounts/login/', patient_login_view, name='account_login'),

    # # Social Authentication
    # path('accounts/', include('allauth.urls')),
]

# Static and Media Files (Development Only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)