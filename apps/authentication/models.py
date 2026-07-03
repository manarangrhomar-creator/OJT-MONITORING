import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta
from apps.core.models import User, BaseModel


class PasswordResetOTP(BaseModel):
    """Store OTP codes for password reset."""
    email = models.EmailField(db_index=True)
    otp = models.CharField(max_length=6, db_index=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {'Used' if self.is_used else 'Active'}"

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    @classmethod
    def generate_otp(cls, email):
        otp_code = f"{secrets.randbelow(900000) + 100000}"
        return cls.objects.create(
            email=email,
            otp=otp_code,
            expires_at=timezone.now() + timedelta(minutes=15)
        )


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
