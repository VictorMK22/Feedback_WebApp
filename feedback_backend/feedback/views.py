# Django core functionality
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import Prefetch
from django.utils import timezone
from django.http import JsonResponse
from .forms import FeedbackForm
from django.utils.translation import gettext as _
from django.contrib import messages
import logging
from django.views.decorators.http import require_POST

# Application models
from .models import Feedback, Response, Notification, CustomUser

# Utilities
import os
from datetime import datetime
from googletrans import Translator

logger = logging.getLogger(__name__)

@login_required
def home_dashboard(request):
    try:
        username = request.user.username
        profile_image_url = None

        if hasattr(request.user, 'profile') and request.user.profile.profile_picture:
            profile_image_url = request.user.profile.profile_picture.url

        # Feedback filtering
        if request.user.role == 'Patient':
            feedbacks = Feedback.objects.filter(user=request.user)
        else:
            feedbacks = Feedback.objects.all()

        feedbacks = feedbacks.order_by('-created_at')[:5].prefetch_related(
            Prefetch('responses', queryset=Response.objects.order_by('-created_at'))
        )

        # Feedback list + responses
        feedback_data = []
        total_responses = 0
        for fb in feedbacks:
            responses = list(fb.responses.all())
            total_responses += 1
            feedback_data.append({
                "feedback": fb,
                "responses": responses
            })

        # Notifications (latest 10)
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-timestamp')[:10]

        # Unread notifications count
        unread_notifications = Notification.objects.filter(
            user=request.user,
            status='Unread'
        ).count()

        context = {
            "username": username,
            "profile_image_url": profile_image_url,
            "feedback_data": feedback_data,
            "notifications": notifications,
            "total_responses": total_responses,
            "feedbacks_count": feedbacks.count(),     # FIXED
            "unread_notifications": unread_notifications,  # FIXED
        }

        return render(request, 'dashboard/home.html', context)

    except Exception as e:
        logger.exception("home_dashboard error: %s", e)
        return render(request, 'error.html', {"error": str(e)})

@login_required
def feedback_list(request):
    try:
        if request.user.role == 'Patient':
            feedbacks = Feedback.objects.filter(user=request.user)
        else:
            feedbacks = Feedback.objects.all()
        
        # Remove 'attachments' from prefetch_related since it's a JSONField
        feedbacks = feedbacks.select_related('user').order_by('-created_at')

        # Add computed properties for template
        for feedback in feedbacks:
            feedback.remaining_rating = 5 - feedback.rating
            # Determine status color
            status_colors = {
                'pending': 'warning',
                'reviewed': 'info',
                'resolved': 'success',
                'closed': 'secondary'
            }
            feedback.status_color = status_colors.get(feedback.status.lower(), 'secondary')

        context = {
            "feedback_list": feedbacks,
            "is_paginated": False,
        }

        return render(request, 'feedback/list.html', context)
    except Exception as e:
        return render(request, 'error.html', {"error": str(e)})

@login_required
def feedback_create(request):
    if request.user.role != 'Patient':
        messages.error(request, _("Only patients can submit feedback."))
        return redirect('feedback:feedback-list')
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            try:
                feedback = form.save(commit=False)
                feedback.user = request.user
                
                # Get rating from POST data
                rating = request.POST.get('rating', 0)
                try:
                    feedback.rating = int(rating)
                    if not (1 <= feedback.rating <= 5):
                        raise ValueError("Rating must be between 1 and 5")
                except (ValueError, TypeError):
                    messages.error(request, _("Please select a valid rating (1-5)."))
                    return render(request, 'feedback/create.html', {'form': form})
                
                # Save feedback first to get an ID
                feedback.save()
                
                # Handle file attachments - Store paths in JSONField
                uploaded_files = request.FILES.getlist('attachments')
                if uploaded_files:
                    saved_files = []
                    for file in uploaded_files:
                        # Validate file size (5MB max)
                        if file.size > 5 * 1024 * 1024:
                            messages.warning(
                                request,
                                _("File '%(filename)s' exceeds 5MB and was skipped.") % {'filename': file.name}
                            )
                            continue
                        
                        # Validate file extension
                        ext = os.path.splitext(file.name)[1].lower()
                        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                        
                        if ext not in allowed_extensions:
                            messages.warning(
                                request,
                                _("File '%(filename)s' has invalid format and was skipped.") % {'filename': file.name}
                            )
                            continue
                        
                        # Save file to storage
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"feedback_{feedback.id}_{timestamp}{ext}"
                        path = default_storage.save(f"feedback_attachments/{filename}", file)
                        saved_files.append(path)
                    
                    # Update the attachments JSONField
                    if saved_files:
                        feedback.attachments = saved_files
                        feedback.save()
                
                messages.success(request, _("Thank you for your feedback!"))
                return redirect('feedback:feedback-list')
                
            except Exception as e:
                logger.error(f"Error creating feedback: {str(e)}", exc_info=True)
                messages.error(request, _("An error occurred: %(error)s") % {'error': str(e)})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FeedbackForm()
    
    return render(request, 'feedback/create.html', {'form': form})

@login_required
def feedback_detail(request, pk):
    try:
        feedback = get_object_or_404(Feedback, pk=pk)
        
        # Check permissions
        if request.user.role == 'Patient' and feedback.user != request.user:
            return render(request, 'unauthorized.html', {
                "error": "You can only view your own feedback."
            })
        
        # Add computed properties (same as in feedback_list)
        feedback.remaining_rating = 5 - feedback.rating
        
        # Determine status color
        status_colors = {
            'pending': 'warning',
            'reviewed': 'info',
            'resolved': 'success',
            'closed': 'secondary'
        }
        feedback.status_color = status_colors.get(feedback.status.lower(), 'secondary')
        
        # Get responses for this feedback
        responses = Response.objects.filter(
            feedback=feedback
        ).select_related('responder').order_by('-created_at')
        
        context = {
            'feedback': feedback,
            'responses': responses,
        }
        
        return render(request, 'feedback/detail.html', context)
    except Exception as e:
        return render(request, 'error.html', {"error": str(e)})

@login_required
def feedback_update(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    
    # Check permissions
    if request.user != feedback.user:
        return render(request, 'unauthorized.html', {
            "error": "You can only edit your own feedback."
        })
    
    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            try:
                feedback = form.save(commit=False)
                
                # Update rating if provided
                rating = request.POST.get('rating')
                if rating:
                    try:
                        feedback.rating = int(rating)
                        if not (1 <= feedback.rating <= 5):
                            raise ValueError("Rating must be between 1 and 5")
                    except (ValueError, TypeError):
                        messages.error(request, _("Please select a valid rating (1-5)."))
                        return render(request, 'feedback/update.html', {
                            'form': form,
                            'feedback': feedback
                        })
                
                feedback.save()
                
                # Handle new attachments - ADD to existing ones
                uploaded_files = request.FILES.getlist('attachments')
                if uploaded_files:
                    # Get existing attachments or start with empty list
                    existing_attachments = feedback.attachments if feedback.attachments else []
                    new_files = []
                    
                    for file in uploaded_files:
                        # Validate file size
                        if file.size > 5 * 1024 * 1024:
                            messages.warning(
                                request,
                                _("File '%(filename)s' exceeds 5MB and was skipped.") % {'filename': file.name}
                            )
                            continue
                        
                        # Validate file type
                        ext = os.path.splitext(file.name)[1].lower()
                        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
                        
                        if ext not in allowed_extensions:
                            messages.warning(
                                request,
                                _("File '%(filename)s' has invalid format and was skipped.") % {'filename': file.name}
                            )
                            continue
                        
                        # Save file
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"feedback_{feedback.id}_{timestamp}{ext}"
                        path = default_storage.save(f"feedback_attachments/{filename}", file)
                        new_files.append(path)
                    
                    # Combine existing and new attachments
                    if new_files:
                        feedback.attachments = existing_attachments + new_files
                        feedback.save()
                
                messages.success(request, _("Feedback updated successfully!"))
                return redirect('feedback:feedback-detail', pk=feedback.pk)
                
            except Exception as e:
                logger.error(f"Error updating feedback: {str(e)}", exc_info=True)
                messages.error(request, _("An error occurred: %(error)s") % {'error': str(e)})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FeedbackForm(instance=feedback)
    
    return render(request, 'feedback/update.html', {
        'form': form,
        'feedback': feedback
    })
    
@login_required
def feedback_delete(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    
    # Check permissions
    if request.user != feedback.user:
        return render(request, 'unauthorized.html', {
            "error": "You can only delete your own feedback."
        })
    
    if request.method == 'POST':
        try:
            # Delete associated files from storage
            if feedback.attachments:
                for attachment_path in feedback.attachments:
                    try:
                        if default_storage.exists(attachment_path):
                            default_storage.delete(attachment_path)
                    except Exception as e:
                        logger.warning(f"Error deleting file {attachment_path}: {e}")
            
            # Delete the feedback
            feedback.delete()
            
            messages.success(request, _("Feedback deleted successfully."))
            return redirect('feedback:feedback-list')
            
        except Exception as e:
            logger.error(f"Error deleting feedback: {str(e)}", exc_info=True)
            messages.error(request, _("An error occurred while deleting: %(error)s") % {'error': str(e)})
            return redirect('feedback:feedback-detail', pk=pk)
    
    return render(request, 'feedback/delete_confirm.html', {'feedback': feedback})

@login_required
def response_create(request, feedback_id):
    if request.user.role != 'Admin':
        return render(request, 'unauthorized.html', {"error": "Only admins can respond to feedback."})
    
    if request.method == 'POST':
        try:
            data = {
                'feedback': feedback_id,
                'responder': request.user.id,
                'response_text': request.POST.get('response_text')
            }

            serializer = ResponseSerializer(data=data)
            if serializer.is_valid():
                response = serializer.save()

                # Notify feedback owner
                feedback = response.feedback
                Notification.objects.create(
                    user=feedback.user,
                    message=f"Response from admin to your feedback ID {feedback.id}",
                    feedback=feedback
                )

                return redirect('feedback:feedback-list')
            else:
                return render(request, 'feedback/respond.html', {
                    "errors": serializer.errors, 
                    "feedback_id": feedback_id
                })
        except Exception as e:
            return render(request, 'error.html', {"error": str(e)})
    
    return render(request, 'feedback/respond.html', {"feedback_id": feedback_id})


@login_required
def notification_list(request):
    try:
        notifications = Notification.objects.filter(user=request.user).order_by('-timestamp')
        return render(request, 'notifications/list.html', {
            "notifications": notifications
        })
    except Exception as e:
        logger.exception("notification_list error: %s", e)
        return render(request, 'error.html', {
            "error": str(e),
            "status_code": 500
        })

@login_required
def notification_detail(request, notification_id):
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )

        # Optional: mark as read when opened
        if notification.status == 'Unread':
            notification.status = 'Read'
            notification.save(update_fields=['status'])

        return render(request, 'notifications/detail.html', {
            "notification": notification
        })

    except Exception as e:
        logger.exception("notification_detail error: %s", e)
        return render(request, 'error.html', {
            "error": str(e),
            "status_code": 500
        })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Marks a single notification as Read.
    """
    try:
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.status = 'Read'   # use status field, not .read
        notification.save()
        logger.info("User %s marked notification %s as Read", request.user.username, notification_id)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.exception("mark_notification_read error: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
@require_POST
def mark_all_read(request):
    """
    Marks all unread notifications for the user as Read.
    """
    try:
        updated_count = Notification.objects.filter(user=request.user, status='Unread').update(status='Read')
        logger.info("User %s marked %d notifications as Read", request.user.username, updated_count)
        return JsonResponse({'status': 'success', 'updated_count': updated_count})
    except Exception as e:
        logger.exception("mark_all_read error: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def delete_notification(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.delete()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
    except Exception as e:
        logger.exception("delete_notification error: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
@login_required
def clear_all_notifications(request):
    """
    Deletes all notifications for the current user.
    """
    try:
        deleted, _ = Notification.objects.filter(user=request.user).delete()
        logger.info("User %s cleared %d notifications", request.user.username, deleted)
        return JsonResponse({'status': 'success', 'deleted_count': deleted})
    except Exception as e:
        logger.exception("clear_all_notifications error: %s", e)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def translate_text(request):
    if request.method == 'POST':
        try:
            text = request.POST.get('text')
            target_lang = request.POST.get('target_language', 'en')

            translator = Translator()
            translation = translator.translate(text, dest=target_lang)

            return render(request, 'translate/result.html', {
                "original_text": text,
                "translated_text": translation.text,
                "detected_lang": translation.src
            })
        except Exception as e:
            return render(request, 'error.html', {"error": str(e)})
    
    return render(request, 'translate/form.html')
