from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


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
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient_email],
        )
        email.attach_alternative(html_content, 'text/html')
        email.send(fail_silently=True)
    except Exception as exc:
        raise self.retry(exc=exc)
