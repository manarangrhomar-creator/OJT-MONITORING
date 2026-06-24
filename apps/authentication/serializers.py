from rest_framework import serializers
from apps.core.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import PasswordResetOTP


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password', 'password2', 'role', 'phone_number', 'course', 'faculty_id')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'course': {'required': False},
            'faculty_id': {'required': False},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        identifier = attrs['identifier']
        password = attrs['password']

        found_user = None

        user = authenticate(username=identifier, password=password)
        if user:
            if user.role == 'coordinator' and user.approval_status != 'approved':
                raise serializers.ValidationError("Your coordinator account is pending approval. Please wait for an admin to approve your account.")
            if user.role == 'student' and user.approval_status != 'approved':
                raise serializers.ValidationError("Your student account is pending approval. Please wait for your coordinator to approve your account.")
            attrs['user'] = user
            return attrs

        try:
            found_user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            pass

        if not found_user:
            try:
                from apps.student.models import StudentProfile
                profile = StudentProfile.objects.get(student_id=identifier)
                found_user = profile.user
            except (ImportError, Exception):
                pass

        if found_user:
            user = authenticate(username=found_user.username, password=password)
            if user:
                if user.role == 'coordinator' and user.approval_status != 'approved':
                    raise serializers.ValidationError("Your coordinator account is pending approval. Please wait for an admin to approve your account.")
                if user.role == 'student' and user.approval_status != 'approved':
                    raise serializers.ValidationError("Your student account is pending approval. Please wait for your coordinator to approve your account.")
                attrs['user'] = user
                return attrs
            raise serializers.ValidationError("Invalid password.")

        raise serializers.ValidationError("No account found with that email or ID.")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    full_name = serializers.SerializerMethodField()
    course_name = serializers.CharField(source='course.name', read_only=True, allow_null=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role', 'phone_number', 'profile_picture', 'faculty_id', 'is_active', 'created_at', 'course', 'course_name')
        read_only_fields = ('id', 'created_at')
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP."""
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email.")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            otp_record = PasswordResetOTP.objects.filter(
                email=attrs['email'],
                otp=attrs['otp'],
                is_used=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")

        if not otp_record.is_valid():
            raise serializers.ValidationError("OTP has expired.")
        attrs['otp_record'] = otp_record
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for resetting password."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
            otp_record = PasswordResetOTP.objects.filter(
                email=attrs['email'],
                otp=attrs['otp'],
                is_used=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP.")
        if not otp_record.is_valid():
            raise serializers.ValidationError("OTP has expired.")
        attrs['otp_record'] = otp_record
        return attrs
