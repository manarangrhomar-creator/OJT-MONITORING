from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from pathlib import Path
from email.mime.image import MIMEImage


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

        image_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'isu_new_seal_512x512.png'
        if image_path.exists():
            with open(image_path, 'rb') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header('Content-ID', '<isu_logo>')
                img.add_header('Content-Disposition', 'inline', filename='isu_new_seal_512x512.png')
                email.attach(img)

        email.send(fail_silently=False)
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception('Failed to send approval email to %s', recipient_email)
        raise self.retry(exc=exc)
