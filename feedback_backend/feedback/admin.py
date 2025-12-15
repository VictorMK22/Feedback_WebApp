from django.contrib import admin
from .models import Feedback, Response, Notification

# Register your models here.

admin.site.register(Feedback)
admin.site.register(Response)
admin.site.register(Notification)
