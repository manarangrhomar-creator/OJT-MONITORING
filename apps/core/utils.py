"""
Utils for the application
"""
import os
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notification
from .tasks import send_email_task


def _attach_logo(email):
    """Attach the ISU logo as an inline image with Content-ID."""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'isu_new_seal_512x512.png')
    if os.path.exists(logo_path):
        from email.mime.image import MIMEImage
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read(), _subtype='png')
            img.add_header('Content-ID', '<isu_logo>')
            img.add_header('Content-Disposition', 'inline', filename='isu_logo.png')
            email.attach(img)


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
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        type=type,
        related_object_id=related_object.id if related_object else None,
        related_object_type=related_object_type,
    )
    _send_websocket_notification(recipient, notification)


def _send_websocket_notification(recipient, notification):
    try:
        channel_layer = get_channel_layer()
        unread_count = Notification.objects.filter(recipient=recipient, is_read=False).count()
        cache.delete(f'unread_count_{recipient.id}')
        async_to_sync(channel_layer.group_send)(
            f'notifications_{recipient.id}',
            {
                'type': 'notification_message',
                'count': unread_count,
                'notification': {
                    'id': str(notification.id),
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.type,
                    'is_read': notification.is_read,
                    'created_at': notification.created_at.isoformat(),
                    'related_object_type': notification.related_object_type,
                    'related_object_id': str(notification.related_object_id) if notification.related_object_id else None,
                },
            }
        )
    except Exception:
        pass


def send_unread_count_update(recipient):
    """Push the current unread count to the recipient via WebSocket."""
    try:
        channel_layer = get_channel_layer()
        cache.delete(f'unread_count_{recipient.id}')
        unread_count = Notification.objects.filter(recipient=recipient, is_read=False).count()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{recipient.id}',
            {
                'type': 'unread_count',
                'count': unread_count,
            }
        )
    except Exception:
        pass


def send_notification_email(recipient, subject, message, title='', site_url=None):
    """Send an HTML email notification using the branded email template."""
    if not recipient.email:
        return

    recipient_name = recipient.get_full_name() or recipient.username
    context = {
        'recipient_name': recipient_name,
        'subject': subject,
        'title': title or subject,
        'message': message,
        'site_url': site_url or getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    html_content = render_to_string('emails/notification_email.html', context)
    plain_message = f'Dear {recipient_name},\n\n{message}\n\nBest regards,\nISU OJT Monitoring System'

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.EMAIL_HOST_USER,
        to=[recipient.email],
    )
    email.attach_alternative(html_content, 'text/html')
    _attach_logo(email)
    email.send(fail_silently=True)


def broadcast_dashboard_update(section=''):
    """Broadcast a dashboard refresh event to all connected dashboards."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard_refresh',
                'section': section,
            }
        )
    except Exception:
        pass


def create_and_send_notification(recipient, title, message, type='general',
                                 related_object=None, related_object_type='',
                                 email_subject=None):
    """Create an in-app notification and send an email notification asynchronously."""
    create_notification(
        recipient=recipient,
        title=title,
        message=message,
        type=type,
        related_object=related_object,
        related_object_type=related_object_type,
    )
    if recipient.email:
        recipient_name = recipient.get_full_name() or recipient.username
        send_email_task.delay(
            recipient_email=recipient.email,
            subject=email_subject or title,
            message=message,
            title=title,
            recipient_name=recipient_name,
        )
