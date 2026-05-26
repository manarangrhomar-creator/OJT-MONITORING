from rest_framework import serializers
from apps.core.models import User
from .models import StudentProfile, FacialRecognition


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
