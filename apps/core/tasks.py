from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.db import models
from pathlib import Path
from email.mime.image import MIMEImage


def _attach_logo(email):
    """Attach the ISU logo as an inline image with Content-ID."""
    logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'isu_new_seal_512x512.png'
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read(), _subtype='png')
            img.add_header('Content-ID', '<isu_logo>')
            img.add_header('Content-Disposition', 'inline', filename='isu_logo.png')
            email.attach(img)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, recipient_email, subject, message, title='', recipient_name='', site_url=None):
    if not recipient_email:
        return

    context = {
        'recipient_name': recipient_name or 'User',
        'subject': subject,
        'title': title or subject,
        'message': message,
        'site_url': site_url or getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }

    html_content = render_to_string('emails/notification_email.html', context)
    plain_message = (
        f'Dear {recipient_name},\n\n{message}\n\n'
        f'Best regards,\nISU OJT Monitoring System'
    )

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER or 'noreply@localhost',
            to=[recipient_email],
        )
        email.attach_alternative(html_content, 'text/html')
        _attach_logo(email)
        email.send(fail_silently=False)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception('Failed to send approval email to %s', recipient_email)
        raise self.retry(exc=exc)


AUTO_TIMEOUT_HOURS = 10  # ponytail: hardcoded; move to settings if different sites need different thresholds


@shared_task(bind=True)
def auto_clockout_stale_attendances(self):
    """Auto clock-out students still checked-in after AUTO_TIMEOUT_HOURS and create flags."""
    from django.utils import timezone
    from datetime import time
    from apps.coordinator.models import Attendance, FlagRecord
    from apps.core.utils import create_notification

    now = timezone.now()
    cutoff = now - timezone.timedelta(hours=AUTO_TIMEOUT_HOURS)
    stale = Attendance.objects.filter(
        time_out__isnull=True,
        created_at__lte=cutoff,
    ).select_related('student', 'program')

    count = 0
    for att in stale:
        att.time_out = now.time()
        att.auto_clocked_out = True
        att.save(update_fields=['time_out', 'auto_clocked_out'])

        FlagRecord.objects.get_or_create(
            attendance=att,
            flag_type='auto_timeout',
            defaults={'reason': f'No clock-out after {AUTO_TIMEOUT_HOURS}h. Auto clocked-out at {att.time_out}.'},
        )
        create_notification(
            recipient=att.student,
            title='Auto Clock-Out',
            message=f'You were automatically clocked out at {att.time_out} because no manual clock-out was recorded.',
            type='general',
        )
        count += 1

    return f'Auto clocked-out {count} stale attendances'


@shared_task
def cleanup_expired_security_records():
    """Delete expired/old security records based on DATA_RETENTION_DAYS.

    Cleans up:
    - PasswordResetOTP: used or expired records
    - LoginAttempt: records older than retention period
    - EmailVerificationToken: verified or expired records
    """
    from django.utils import timezone
    from django.conf import settings
    from apps.authentication.models import PasswordResetOTP, LoginAttempt, EmailVerificationToken

    retention_days = getattr(settings, 'DATA_RETENTION_DAYS', 30)
    cutoff = timezone.now() - timezone.timedelta(days=retention_days)

    otp_deleted, _ = PasswordResetOTP.objects.filter(
        models.Q(is_used=True) | models.Q(expires_at__lt=cutoff)
    ).delete()

    login_deleted, _ = LoginAttempt.objects.filter(
        created_at__lt=cutoff
    ).delete()

    token_deleted, _ = EmailVerificationToken.objects.filter(
        models.Q(verified=True) | models.Q(expires_at__lt=cutoff)
    ).delete()

    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        'Security record cleanup: %d OTPs, %d login attempts, %d verification tokens deleted',
        otp_deleted, login_deleted, token_deleted,
    )

    return f'Cleaned up {otp_deleted} OTPs, {login_deleted} login attempts, {token_deleted} verification tokens'
