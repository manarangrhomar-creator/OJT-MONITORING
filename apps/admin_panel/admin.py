from django.contrib import admin
from .models import SystemLog, SystemSettings


@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('get_activity_type', 'admin_user', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('admin_user__username', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def get_activity_type(self, obj):
        return obj.get_activity_type_display()
    get_activity_type.short_description = 'Activity'


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)
