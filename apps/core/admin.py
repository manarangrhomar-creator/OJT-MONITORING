from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {'fields': ('id', 'username', 'email', 'first_name', 'last_name', 'phone_number', 'profile_picture')}),
        ('Role & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make role read-only for superusers since it's auto-assigned."""
        readonly = list(self.readonly_fields)
        if obj and obj.is_superuser:
            readonly.append('role')
        return readonly
