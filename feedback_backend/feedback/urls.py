from django.urls import path
from .views import (
    home_dashboard, 
    feedback_list, 
    feedback_create,
    feedback_detail,      
    feedback_update,
    feedback_delete,      
    response_create, 
    notification_list,
    notification_detail,
    mark_notification_read,
    mark_all_read,
    clear_all_notifications,
    delete_notification,
    translate_text
)

app_name = "feedback"

urlpatterns = [
    # Dashboard (root URL)
    path('', home_dashboard, name='home-dashboard'),
    
    # Feedback endpoints
    path('feedback/', feedback_list, name='feedback-list'),
    path('feedback/create/', feedback_create, name='feedback-create'),
    path('feedback/<int:pk>/', feedback_detail, name='feedback-detail'),
    path('feedback/<int:pk>/edit/', feedback_update, name='feedback-update'),
    path('feedback/<int:pk>/delete/', feedback_delete, name='feedback-delete'),  
    
    # Response endpoints
    path('feedback/<int:feedback_id>/respond/', 
         response_create, 
         name='response-create'),
    
    # Notification endpoints
    path('notifications/', notification_list, name='notification-list'),
    path('notifications/<int:notification_id>/detail', notification_detail, name='notification-detail'),
    path('notifications/<int:notification_id>/mark-read/', 
         mark_notification_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', mark_all_read, name='mark-all-read'),
    path('notifications/clear-all/', clear_all_notifications, name='clear-all'),
    path('notifications/<int:notification_id>/delete/', delete_notification, name='delete-notification'),
    
    # Utility endpoints
    path('translate/', translate_text, name='translate-text'),
]