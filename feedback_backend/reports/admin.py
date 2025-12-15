# admin.py
from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'period_start', 'period_end', 'admin', 'status')
    list_filter = ('report_type', 'status', 'generated_at')
    search_fields = ('admin__email', 'notes')
    date_hierarchy = 'generated_at'