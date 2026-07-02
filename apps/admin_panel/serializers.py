from rest_framework import serializers
from apps.core.models import User, Course
from apps.coordinator.models import Site, OJTProgram, OJTApplication, SiteAssignment
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
    course_name = serializers.SerializerMethodField()
    coordinator_name = serializers.SerializerMethodField()

    class Meta:
        model = Site
        fields = ('id', 'name', 'course', 'course_name', 'coordinator', 'coordinator_name', 'supervisor_name', 'contact_number', 'is_active', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_course_name(self, obj):
        return obj.course.name if obj.course else 'All Courses'

    def get_coordinator_name(self, obj):
        return obj.coordinator.get_full_name() or obj.coordinator.username if obj.coordinator else None


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer for system logs."""
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)
    
    class Meta:
        model = SystemLog
        fields = ('id', 'activity_type', 'description', 'admin_user', 'admin_username', 'created_at')
        read_only_fields = ('id', 'created_at')


class AdminProgramSerializer(serializers.ModelSerializer):
    """Serializer for admin program management."""
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = OJTProgram
        fields = ('id', 'name', 'description', 'start_date', 'end_date', 'status',
                  'coordinator', 'coordinator_name', 'max_students', 'student_count',
                  'location', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_student_count(self, obj):
        return obj.applications.filter(status='approved').count()


class AdminProgramStudentSerializer(serializers.Serializer):
    """Serializer for listing students in a program."""
    student_id = serializers.UUIDField(source='student.id')
    student_name = serializers.CharField(source='student.get_full_name')
    email = serializers.EmailField(source='student.email')
    course = serializers.SerializerMethodField()
    student_id_number = serializers.SerializerMethodField()
    application_status = serializers.CharField(source='status')
    site_name = serializers.SerializerMethodField()
    supervisor_name = serializers.SerializerMethodField()

    def get_course(self, obj):
        profile = getattr(obj.student, 'student_profile', None)
        if profile and profile.course:
            return profile.course.name
        return ''

    def get_student_id_number(self, obj):
        profile = getattr(obj.student, 'student_profile', None)
        if profile:
            return profile.student_id
        return ''

    def get_site_name(self, obj):
        assignment = SiteAssignment.objects.filter(student=obj.student, program=obj.program).first()
        if assignment:
            return assignment.site.name if assignment.site else 'Not assigned'
        return 'Not assigned'

    def get_supervisor_name(self, obj):
        assignment = SiteAssignment.objects.filter(student=obj.student, program=obj.program).first()
        return assignment.supervisor_name or '' if assignment else ''


class CoordinatorChoiceSerializer(serializers.Serializer):
    """Serializer for coordinator dropdown."""
    id = serializers.UUIDField()
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    course_name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_course_name(self, obj):
        return obj.course.name if obj.course else ''
