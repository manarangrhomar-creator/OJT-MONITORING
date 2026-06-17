from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import URLValidator
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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    course = models.CharField(max_length=255, blank=True, null=True, help_text="Course/Program the coordinator oversees")
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    faculty_id = models.ImageField(upload_to='faculty_ids/', blank=True, null=True, help_text="Upload faculty ID card")
    is_active = models.BooleanField(default=True)
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
