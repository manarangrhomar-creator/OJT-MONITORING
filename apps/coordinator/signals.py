from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SiteAssignment
from apps.core.utils import create_and_send_notification


@receiver(post_save, sender=SiteAssignment)
def notify_student_on_site_assignment(sender, instance, created, **kwargs):
    student = instance.student
    site_name = instance.site.name if instance.site else 'TBD'
    supervisor = instance.supervisor_name or 'TBD'
    supervisor_contact = instance.supervisor_contact or 'TBD'
    program_name = instance.program.name

    site_info = f'Program: {program_name}, Site: {site_name}, Supervisor: {supervisor}, Contact: {supervisor_contact}'

    create_and_send_notification(
        recipient=student,
        title='Site Assignment',
        message=(
            f'You have been assigned to {site_name} under the {program_name} program. '
            f'Supervisor: {supervisor}, Contact: {supervisor_contact}.'
        ),
        type='site_assignment',
        related_object=instance,
        related_object_type='SiteAssignment',
        email_subject=f'OJT Site Assignment - {site_name}',
    )
