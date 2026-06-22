from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import SiteAssignment
from apps.core.models import Notification


@receiver(post_save, sender=SiteAssignment)
def notify_student_on_site_assignment(sender, instance, created, **kwargs):
    student = instance.student
    site_name = instance.site.name if instance.site else 'TBD'
    site = instance.site
    supervisor = instance.supervisor_name or 'TBD'
    supervisor_contact = instance.supervisor_contact or 'TBD'
    program_name = instance.program.name

    title = 'Site Assignment'
    message = (
        f'You have been assigned to {site_name} under the {program_name} program. '
        f'Supervisor: {supervisor}, Contact: {supervisor_contact}.'
    )

    Notification.objects.create(
        recipient=student,
        title=title,
        message=message,
        type='site_assignment',
        related_object_id=instance.id,
        related_object_type='SiteAssignment',
    )

    if student.email:
        subject = f'OJT Site Assignment - {site_name}'
        email_message = (
            f'Dear {student.get_full_name() or student.username},\n\n'
            f'You have been assigned to a site for your On-the-Job Training.\n\n'
            f'Program: {program_name}\n'
            f'Site: {site_name}\n'
            f'Supervisor: {supervisor}\n'
            f'Supervisor Contact: {supervisor_contact}\n'
            f'Assigned Date: {instance.assigned_date}\n\n'
            f'Please log in to the OJT portal for more details.\n\n'
            f'Best regards,\nISU OJT Monitoring System'
        )
        send_mail(
            subject=subject,
            message=email_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[student.email],
            fail_silently=True,
        )
