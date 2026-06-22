"""
Utils for the application
"""
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification


def get_week_range(date=None):
    """Get the start and end date of the week."""
    if date is None:
        date = datetime.now().date()
    
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start, end


def get_month_range(date=None):
    """Get the start and end date of the month."""
    if date is None:
        date = datetime.now().date()
    
    if date.month == 12:
        end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = date.replace(month=date.month + 1, day=1) - timedelta(days=1)
    
    start = date.replace(day=1)
    return start, end


def create_notification(recipient, title, message, type='general', related_object=None, related_object_type=''):
    Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        type=type,
        related_object_id=related_object.id if related_object else None,
        related_object_type=related_object_type,
    )


def send_notification_email(recipient, subject, message):
    if recipient.email:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient.email],
            fail_silently=True,
        )
