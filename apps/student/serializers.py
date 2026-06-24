from rest_framework import serializers
from apps.core.models import User
from apps.coordinator.models import OJTProgram, OJTApplication
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


class StudentProgramSerializer(serializers.ModelSerializer):
    """Lightweight program view for students."""
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = OJTProgram
        fields = ('id', 'name', 'description', 'start_date', 'end_date', 'status',
                  'coordinator_name', 'max_students', 'student_count', 'location')

    def get_student_count(self, obj):
        return obj.applications.filter(status='approved').count()


class StudentApplySerializer(serializers.Serializer):
    """Student application submission."""
    program = serializers.PrimaryKeyRelatedField(queryset=OJTProgram.objects.filter(status='active'))
    application_letter = serializers.FileField()
    resume = serializers.FileField(required=False)

    def validate_program(self, value):
        user = self.context['request'].user
        if value.applications.filter(status='approved').count() >= value.max_students:
            raise serializers.ValidationError('This program has reached maximum capacity.')
        if OJTApplication.objects.filter(student=user, program=value).exists():
            raise serializers.ValidationError('You have already applied to this program.')
        return value


class FacialRecognitionSerializer(serializers.ModelSerializer):
    """Serializer for Facial Recognition."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = FacialRecognition
        fields = ('id', 'student', 'student_name', 'is_verified', 'verification_date', 'created_at')
        read_only_fields = ('id', 'created_at', 'verification_date', 'facial_encoding')
