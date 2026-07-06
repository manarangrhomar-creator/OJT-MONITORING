from django.contrib import admin
from .models import LoginAttempt, EmailVerificationToken


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_status', 'ip_address', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def get_status(self, obj):
        return "✓ Success" if obj.success else "✗ Failed"
    get_status.short_description = 'Status'


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'verified', 'expires_at')
    list_filter = ('verified', 'created_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('id', 'token', 'created_at')
