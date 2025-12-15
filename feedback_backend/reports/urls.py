from django.urls import path
from .views import create_report, report_list
urlpatterns = [
    path('create/', create_report, name='report-create'),
    path('', report_list, name='report-list'),
]