from django.db import models
from django.utils import timezone
from users.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator

class Report(models.Model):
    REPORT_TYPES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
        ('ADHOC', 'Ad Hoc'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('ARCHIVED', 'Archived'),
    ]

    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'Admin'},
        related_name='generated_reports'
    )
    report_type = models.CharField(
        max_length=50,
        choices=REPORT_TYPES,
        default='WEEKLY'
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Generation Date"
    )
    period_start = models.DateField(
        verbose_name="Report Period Start"
    )
    period_end = models.DateField(
        verbose_name="Report Period End"
    )
    resolved_feedback_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Resolved Feedback"
    )
    pending_feedback_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Pending Feedback"
    )
    overall_satisfaction_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Satisfaction Score (0-5)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Additional Notes"
    )
    attachment = models.FileField(
        upload_to='reports/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Report File"
    )

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['report_type']),
            models.Index(fields=['generated_at']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(period_end__gte=models.F('period_start')),
                name='period_end_after_start'
            ),
            models.CheckConstraint(
                check=models.Q(overall_satisfaction_score__gte=0.0) & 
                      models.Q(overall_satisfaction_score__lte=5.0),
                name='valid_satisfaction_score'
            ),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} Report ({self.period_start} to {self.period_end})"

    @property
    def is_latest(self):
        try:
            return self == Report.objects.latest('generated_at')
        except Report.DoesNotExist:
            return False
    
    @property
    def satisfaction_percentage(self):
        return (self.overall_satisfaction_score / 5) * 100
    
    @property
    def satisfaction_level(self):
        if self.overall_satisfaction_score >= 4:
            return 'high'
        elif self.overall_satisfaction_score >= 2.5:
            return 'medium'
        return 'low'
    
    @property
    def feedback_total(self):
        return self.resolved_feedback_count + self.pending_feedback_count
    
    @property
    def resolution_rate(self):
        if self.feedback_total == 0:
            return 0
        return (self.resolved_feedback_count / self.feedback_total) * 100
    
    def save(self, *args, **kwargs):
        # Auto-set period dates for standard report types
        if not self.period_start or not self.period_end:
            today = timezone.now().date()
            if self.report_type == 'DAILY':
                self.period_start = today
                self.period_end = today
            elif self.report_type == 'WEEKLY':
                self.period_start = today - timezone.timedelta(days=today.weekday())
                self.period_end = self.period_start + timezone.timedelta(days=6)
            elif self.report_type == 'MONTHLY':
                self.period_start = today.replace(day=1)
                self.period_end = (self.period_start + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(days=1)
        
        super().save(*args, **kwargs)