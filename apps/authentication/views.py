from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from apps.core.models import User, Course
from apps.student.models import StudentProfile
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserSerializer, SendOTPSerializer, VerifyOTPSerializer, ResetPasswordSerializer
from .models import LoginAttempt, PasswordResetOTP


class AuthenticationViewSet(viewsets.ViewSet):
    """ViewSet for authentication operations."""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def register(self, request):
        """Register a new user."""
        data = request.data.copy()
        course_name = data.get('course', '')

        # Resolve course name to Course object
        if course_name:
            try:
                course_obj = Course.objects.get(name=course_name, is_active=True)
                data['course'] = course_obj.id
            except Course.DoesNotExist:
                data['course'] = None
        else:
            data['course'] = None

        serializer = UserRegisterSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()

            # If registering as a student, create StudentProfile
            if user.role == 'student':
                student_id = data.get('student_id', '')
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'student_id': student_id or f"TEMP-{user.username}",
                        'department': '',
                        'course': course_obj if course_name and 'course_obj' in locals() else None,
                        'year_level': 1,
                    }
                )
                # Don't create token or login — wait for coordinator approval
                return Response({
                    'message': 'Student account created successfully. Please wait for your coordinator to approve your account before logging in.',
                    'user': UserSerializer(user).data,
                }, status=status.HTTP_201_CREATED)

            # Create token for the new user (admins/coordinators get immediate access)
            token, created = Token.objects.get_or_create(user=user)
            login(request, user)
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def login(self, request):
        """User login with token authentication."""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Get or create token
            token, created = Token.objects.get_or_create(user=user)
            
            # Create Django session for @login_required views
            login(request, user)
            
            # Log login attempt
            LoginAttempt.objects.create(
                user=user,
                ip_address=self.get_client_ip(request),
                success=True,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_200_OK)
        
        # Log failed login attempt
        username = request.data.get('username', '')
        try:
            user = User.objects.get(username=username)
            LoginAttempt.objects.create(
                user=user,
                ip_address=self.get_client_ip(request),
                success=False,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        except User.DoesNotExist:
            pass
        
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """User logout."""
        # Delete token on logout
        try:
            request.user.auth_token.delete()
        except:
            pass
        
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user details."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change user password."""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny], authentication_classes=[])
    def courses(self, request):
        """Get list of active courses for registration forms."""
        courses = Course.objects.filter(is_active=True).order_by('name')
        return Response([{
            'id': str(c.id),
            'name': c.name,
        } for c in courses])

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def send_otp(self, request):
        """Send OTP for password reset."""
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_record = PasswordResetOTP.generate_otp(email)
            send_mail(
                subject='Your OTP for Password Reset',
                message=f'Your OTP is: {otp_record.otp}\n\nThis code will expire in 15 minutes.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({
                'message': 'OTP sent successfully',
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def verify_otp(self, request):
        """Verify OTP code."""
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reset_password(self, request):
        """Reset password with OTP verification."""
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            otp_record = serializer.validated_data['otp_record']
            user = User.objects.get(email=serializer.validated_data['email'])
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            otp_record.is_used = True
            otp_record.save()
            return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
