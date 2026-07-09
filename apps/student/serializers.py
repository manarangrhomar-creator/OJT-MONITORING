from rest_framework import serializers
from apps.coordinator.models import OJTProgram, OJTApplication, Site
from .models import StudentProfile, FacialRecognition, StudentNarrativeReport


class StudentNarrativeReportSerializer(serializers.ModelSerializer):
    """Serializer for Student Narrative Report."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            log_date = attrs.get('log_date')
            if log_date:
                qs = StudentNarrativeReport.objects.filter(
                    student=request.user, log_date=log_date
                )
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({
                        'log_date': 'You have already submitted a report for this date.'
                    })
        return attrs

    class Meta:
        model = StudentNarrativeReport
        fields = ('id', 'student', 'student_name', 'program', 'program_name', 'log_date', 'topic', 'content', 'photo_1', 'photo_2', 'photo_3', 'photo_4', 'grade', 'feedback', 'graded_by', 'graded_at', 'created_at', 'updated_at')
        read_only_fields = ('id', 'student', 'program', 'grade', 'feedback', 'graded_by', 'graded_at', 'created_at', 'updated_at')


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
    coordinator_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = OJTProgram
        fields = ('id', 'name', 'description', 'start_date', 'end_date', 'status',
                  'coordinator_name', 'max_students', 'student_count', 'location')

    def get_coordinator_name(self, obj):
        if obj.coordinator:
            name = obj.coordinator.get_full_name()
            return name or obj.coordinator.username
        return ''

    def get_student_count(self, obj):
        return obj.applications.filter(status='approved').count()


ALLOWED_DOC_EXTENSIONS = {'.pdf'}

class StudentApplySerializer(serializers.Serializer):
    """Student application submission."""
    program = serializers.PrimaryKeyRelatedField(queryset=OJTProgram.objects.filter(status='active'))
    application_letter = serializers.FileField()
    resume = serializers.FileField(required=False, allow_null=True)
    face_image = serializers.ImageField(required=False, allow_null=True)
    preferred_site = serializers.PrimaryKeyRelatedField(
        queryset=Site.objects.filter(is_active=True),
        required=False, allow_null=True
    )

    def _validate_file_ext(self, value, field_name):
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise serializers.ValidationError(
                f'{field_name}: File type "{ext}" not allowed. Accepted: PDF only.'
            )
        return value

    def validate_application_letter(self, value):
        return self._validate_file_ext(value, 'Application letter')

    def validate_resume(self, value):
        if value:
            return self._validate_file_ext(value, 'Resume')
        return value

    def validate_program(self, value):
        user = self.context['request'].user
        if value.applications.filter(status='approved').count() >= value.max_students:
            raise serializers.ValidationError('This program has reached maximum capacity.')
        existing = OJTApplication.objects.filter(student=user, program=value).first()
        if existing:
            if existing.status == 'rejected':
                return value
            raise serializers.ValidationError('You have already applied to this program.')
        return value


class FacialRecognitionSerializer(serializers.ModelSerializer):
    """Serializer for Facial Recognition."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = FacialRecognition
        fields = ('id', 'student', 'student_name', 'is_verified', 'verification_date', 'created_at')
        read_only_fields = ('id', 'created_at', 'verification_date', 'facial_encoding')
