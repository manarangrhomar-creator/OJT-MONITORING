from rest_framework import serializers
from apps.core.models import User
from .models import StudentProfile, FacialRecognition, StudentNarrativeReport


class StudentNarrativeReportSerializer(serializers.ModelSerializer):
    """Serializer for Student Narrative Report."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)

    class Meta:
        model = StudentNarrativeReport
        fields = ('id', 'student', 'student_name', 'program', 'program_name', 'log_date', 'topic', 'content', 'photo_1', 'photo_2', 'photo_3', 'photo_4', 'grade', 'feedback', 'graded_by', 'graded_at', 'created_at', 'updated_at')
        read_only_fields = ('id', 'student', 'grade', 'feedback', 'graded_by', 'graded_at', 'created_at', 'updated_at')


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for Student Profile."""
    user_details = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ('id', 'user', 'user_details', 'student_id', 'department', 'course', 'year_level', 'gpa', 'created_at')
        read_only_fields = ('id', 'created_at')
    
    def get_user_details(self, obj):
        return {
            'id': str(obj.user.id),
            'username': obj.user.username,
            'email': obj.user.email,
            'full_name': obj.user.get_full_name(),
        }


class FacialRecognitionSerializer(serializers.ModelSerializer):
    """Serializer for Facial Recognition."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = FacialRecognition
        fields = ('id', 'student', 'student_name', 'is_verified', 'verification_date', 'created_at')
        read_only_fields = ('id', 'created_at', 'verification_date', 'facial_encoding')
