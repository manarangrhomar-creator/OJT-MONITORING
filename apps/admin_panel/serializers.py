from rest_framework import serializers
from apps.core.models import User, Course
from apps.coordinator.models import Site
from .models import SystemLog


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""
    course_name = serializers.CharField(source='course.name', read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'approval_status', 'is_active', 'created_at', 'phone_number', 'course', 'course_name', 'faculty_id')
        read_only_fields = ('id', 'created_at')


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""
    class Meta:
        model = Course
        fields = ('id', 'name', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class SiteSerializer(serializers.ModelSerializer):
    """Serializer for Site model (admin)."""
    course_name = serializers.CharField(source='course.name', read_only=True)

    class Meta:
        model = Site
        fields = ('id', 'name', 'course', 'course_name', 'contact_person', 'contact_number', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer for system logs."""
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)
    
    class Meta:
        model = SystemLog
        fields = ('id', 'activity_type', 'description', 'admin_user', 'admin_username', 'created_at')
        read_only_fields = ('id', 'created_at')
