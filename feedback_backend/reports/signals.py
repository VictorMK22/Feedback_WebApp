# signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Report

@receiver(pre_save, sender=Report)
def set_report_period(sender, instance, **kwargs):
    if not instance.period_start or not instance.period_end:
        # Same logic as in save() method
        ...