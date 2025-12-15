from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Feedback, Response, Notification
from users.models import CustomUser
from django.core.mail import send_mail
from django.conf import settings
from vonage import Vonage
import logging
from . import sms_helper

logger = logging.getLogger(__name__)

# Send SMS helper function using Vonage
def send_sms(phone_number, message):
    vonage_client = Vonage(
        api_key=settings.VONAGE_API_KEY,
        api_secret=settings.VONAGE_API_SECRET,
    )

    response = vonage_client.sms.send(
        {
            "from": "Patient Feedback",
            "to": phone_number,
            "text": message,
        }
    )

    message_status = response["messages"][0]["status"]

    if message_status == "0":
        return {"success": True, "response": response}

    return {
        "success": False,
        "error": response["messages"][0].get("error-text", "Unknown error"),
    }
# Notify Admins when Feedback is Submitted
@receiver(post_save, sender=Feedback)
def notify_admin_on_feedback(sender, instance, created, **kwargs):
    """
    When a new Feedback is created:
    - create Notification objects for all Admin users
    - send email/sms according to admin profile preferences
    """
    try:
        if not created:
            return

        admins = CustomUser.objects.filter(role='Admin')
        if not admins.exists():
            logger.info("notify_admin_on_feedback: no admins found to notify.")
            return

        for admin in admins:
            # Create DB notification
            notif = Notification.objects.create(
                user=admin,
                message=f"New feedback from {instance.user.username}: {instance.content[:200]}",
                feedback=instance
            )
            logger.info("Created Notification(id=%s) for admin=%s", notif.id, admin.username)

            # Try to fetch admin profile safely
            profile = getattr(admin, "profile", None)
            message_text = f"New feedback from {instance.user.username}: {instance.content[:200]}"

            try:
                if profile and getattr(profile, "notification_preference", None) == 'SMS' and getattr(profile, "phone_number", None):
                    sms_resp = sms_helper.send_sms(profile.phone_number, message_text)
                    logger.info("SMS send attempt for admin %s: %s", admin.username, sms_resp)
                elif profile and getattr(profile, "notification_preference", None) == 'Email':
                    send_mail(
                        subject="New Feedback Submitted",
                        message=message_text,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[admin.email],
                        fail_silently=False
                    )
                    logger.info("Email sent to admin %s", admin.email)
                elif profile and getattr(profile, "notification_preference", None) == 'Both' and getattr(profile, "phone_number", None):
                    sms_resp = sms_helper.send_sms(profile.phone_number, message_text)
                    send_mail(
                        subject="New Feedback Submitted",
                        message=message_text,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[admin.email],
                        fail_silently=False
                    )
                    logger.info("SMS+Email sent to admin %s", admin.username)
                else:
                    # default fallback: email
                    send_mail(
                        subject="New Feedback Submitted",
                        message=message_text,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[admin.email],
                        fail_silently=False
                    )
                    logger.info("Default email sent to admin %s", admin.email)
            except Exception as e:
                logger.exception("Error sending notification to admin %s: %s", admin.username, e)

    except Exception as e:
        logger.exception("notify_admin_on_feedback failed: %s", e)
        
# Notify Patient when Admin Responds to Feedback
@receiver(post_save, sender=Response)
def notify_patient_on_response(sender, instance, created, **kwargs):
    """
    When a new Response is created:
    - create a Notification object for the feedback owner (patient)
    - send email/sms according to patient profile preferences
    """
    try:
        if not created:
            return

        # Based on your response_create view you supply 'responder' and 'response_text'
        # Response model fields used here: instance.responder, instance.response_text
        feedback = getattr(instance, 'feedback', None)
        if not feedback:
            logger.warning("notify_patient_on_response: response has no feedback (id?).")
            return

        patient = feedback.user
        if not patient:
            logger.warning("notify_patient_on_response: feedback has no user.")
            return

        # Create DB notification
        notif = Notification.objects.create(
            user=patient,
            message=f"Your feedback (ID {feedback.id}) has a new response from {instance.responder.username}: {str(instance.content)[:200]}",
            feedback=feedback
        )
        logger.info("Created Notification(id=%s) for patient=%s", notif.id, patient.username)

        # Send via preferred channel(s)
        profile = getattr(patient, "profile", None)
        message_text = f"Your feedback (ID {feedback.id}) has a new response from {instance.responder.username}."

        try:
            if profile and getattr(profile, "notification_preference", None) == 'SMS' and getattr(profile, "phone_number", None):
                sms_resp = sms_helper.send_sms(profile.phone_number, message_text)
                logger.info("SMS send attempt for patient %s: %s", patient.username, sms_resp)
            elif profile and getattr(profile, "notification_preference", None) == 'Email':
                send_mail(
                    subject="Your Feedback Has Been Responded To",
                    message=message_text,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[patient.email],
                    fail_silently=False
                )
                logger.info("Email sent to patient %s", patient.email)
            elif profile and getattr(profile, "notification_preference", None) == 'Both' and getattr(profile, "phone_number", None):
                sms_resp = sms_helper.send_sms(profile.phone_number, message_text)
                send_mail(
                    subject="Your Feedback Has Been Responded To",
                    message=message_text,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[patient.email],
                    fail_silently=False
                )
                logger.info("SMS+Email sent to patient %s", patient.username)
            else:
                # fallback: email
                send_mail(
                    subject="Your Feedback Has Been Responded To",
                    message=message_text,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[patient.email],
                    fail_silently=False
                )
                logger.info("Fallback email sent to patient %s", patient.email)
        except Exception as e:
            logger.exception("Error sending notification to patient %s: %s", patient.username, e)

    except Exception as e:
        logger.exception("notify_patient_on_response failed: %s", e)
    