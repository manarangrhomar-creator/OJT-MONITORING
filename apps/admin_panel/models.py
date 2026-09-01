from django.db import models
from apps.core.models import BaseModel, User


class SystemLog(BaseModel):
    """Log system activities."""
    ACTIVITY_CHOICES = [
        ('user_created', 'User Created'),
        ('user_deleted', 'User Deleted'),
        ('user_archived', 'User Archived'),
        ('user_restored', 'User Restored'),
        ('program_created', 'Program Created'),
        ('program_deleted', 'Program Deleted'),
        ('program_archived', 'Program Archived'),
        ('program_restored', 'Program Restored'),
        ('approval_made', 'Approval Made'),
        ('report_generated', 'Report Generated'),
    ]
    
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES)
    description = models.TextField()
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='system_logs')
    
    class Meta:
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.created_at}"


class SystemSettings(models.Model):
    """Store system-wide settings."""
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return self.key
