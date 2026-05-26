from rest_framework import serializers
from .models import OJTProgram, OJTApplication, Attendance


class OJTProgramSerializer(serializers.ModelSerializer):
    """Serializer for OJT Program."""
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    student_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OJTProgram
        fields = ('id', 'name', 'description', 'start_date', 'end_date', 'status', 'coordinator', 'coordinator_name', 'max_students', 'student_count', 'location', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_student_count(self, obj):
        return obj.get_student_count()


class OJTApplicationSerializer(serializers.ModelSerializer):
    """Serializer for OJT Application."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = OJTApplication
        fields = ('id', 'student', 'student_name', 'program', 'program_name', 'status', 'application_letter', 'resume', 'approved_date', 'rejection_reason', 'created_at')
        read_only_fields = ('id', 'created_at', 'approved_date')


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for Attendance."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = ('id', 'student', 'student_name', 'program', 'date', 'time_in', 'time_out', 'facial_recognition_used', 'notes', 'created_at')
        read_only_fields = ('id', 'created_at')
