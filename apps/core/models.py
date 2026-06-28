from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class User(AbstractUser):
    """Extended User model with role-based access."""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('coordinator', 'OJT Coordinator'),
        ('student', 'OJT Student'),
    ]

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', db_index=True)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending', db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='coordinators', help_text="Course/Program the coordinator oversees")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    faculty_id = models.ImageField(upload_to='faculty_ids/', blank=True, null=True, help_text="Upload faculty ID card")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_coordinator(self):
        return self.role == 'coordinator'
    
    def is_student(self):
        return self.role == 'student'


@receiver(post_save, sender=User)
def assign_admin_role_to_superuser(sender, instance, created, **kwargs):
    """
    Automatically assign 'admin' role to superusers created in Django admin.
    This ensures superusers can login using the authentication system.
    """
    if instance.is_superuser and instance.role != 'admin':
        instance.role = 'admin'
        instance.save(update_fields=['role'])


class BaseModel(models.Model):
    """Base model with common fields for all models."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='%(class)s_updated')
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class Notification(BaseModel):
    """In-app notification for users."""
    TYPE_CHOICES = [
        ('site_assignment', 'Site Assignment'),
        ('application_update', 'Application Update'),
        ('general', 'General'),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='site_assignment')
    is_read = models.BooleanField(default=False, db_index=True)
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read'], name='idx_notif_recip_read'),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title} -> {self.recipient.username}"


class Course(BaseModel):
    """Course/Program model linking coordinators, students, and sites."""
    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        ordering = ['name']

    def __str__(self):
        return self.name
