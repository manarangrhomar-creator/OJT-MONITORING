from rest_framework import serializers
from .models import OJTProgram, OJTApplication, Attendance, SiteAssignment, FlagRecord


class OJTProgramSerializer(serializers.ModelSerializer):
    """Serializer for OJT Program."""
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    student_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OJTProgram
        fields = ('id', 'name', 'description', 'start_date', 'end_date', 'status', 'coordinator', 'coordinator_name', 'max_students', 'student_count', 'location', 'created_at')
        read_only_fields = ('id', 'coordinator', 'created_at')
    
    def get_student_count(self, obj):
        return obj.get_student_count()


class OJTApplicationSerializer(serializers.ModelSerializer):
    """Serializer for OJT Application."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    preferred_site_name = serializers.CharField(source='preferred_site.name', read_only=True, default=None)
    
    class Meta:
        model = OJTApplication
        fields = ('id', 'student', 'student_name', 'program', 'program_name', 'preferred_site', 'preferred_site_name', 'status', 'application_letter', 'resume', 'approved_date', 'rejection_reason', 'created_at')
        read_only_fields = ('id', 'created_at', 'approved_date')


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = ('id', 'student', 'student_name', 'program', 'date', 'time_in', 'time_out', 'facial_recognition_used', 'notes', 'latitude', 'longitude', 'ip_address', 'auto_clocked_out', 'created_at')
        read_only_fields = ('id', 'created_at')



class SiteAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Site Assignment."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True, allow_null=True)
    site_location = serializers.CharField(source='site.name', read_only=True, allow_null=True)

    class Meta:
        model = SiteAssignment
        fields = ('id', 'student', 'student_name', 'program', 'program_name', 'assigned_date', 'site', 'site_name', 'site_location', 'supervisor_name', 'supervisor_contact', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'assigned_date')


class FlagRecordSerializer(serializers.ModelSerializer):
    """Serializer for Flag Records."""
    student_name = serializers.CharField(source='attendance.student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='attendance.program.name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True, default='')

    class Meta:
        model = FlagRecord
        fields = ('id', 'attendance', 'flag_type', 'reason', 'resolved', 'resolved_by', 'resolved_by_name', 'resolved_at', 'student_name', 'program_name', 'created_at')
        read_only_fields = ('id', 'created_at', 'resolved_at')
