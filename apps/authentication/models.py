from django.db import models
from apps.core.models import User, BaseModel


class LoginAttempt(BaseModel):
    """Track login attempts for security."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_attempts')
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status()} - {self.created_at}"
    
    def get_status(self):
        return "Success" if self.success else "Failed"
