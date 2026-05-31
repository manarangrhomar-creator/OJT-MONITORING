from rest_framework import serializers
from apps.core.models import User
from .models import SystemLog


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'approval_status', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer for system logs."""
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)
    
    class Meta:
        model = SystemLog
        fields = ('id', 'activity_type', 'description', 'admin_user', 'admin_username', 'created_at')
        read_only_fields = ('id', 'created_at')
