from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.core.models import User, Course
from apps.student.models import StudentProfile
from apps.core.utils import create_notification, broadcast_dashboard_update
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
        # Ensure file uploads are included in the data dict
        for key in request.FILES:
            data[key] = request.FILES[key]
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

            # Notify admins when a new coordinator registers
            if user.role == 'coordinator':
                try:
                    admins = User.objects.filter(role='admin', is_active=True)
                    for admin in admins:
                        create_notification(
                            recipient=admin,
                            title='New Coordinator Registration',
                            message=f'A new coordinator ({user.get_full_name() or user.email}) has registered and is pending approval.',
                            type='general',
                            related_object=user,
                            related_object_type='coordinator_registration',
                        )
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create admin notification for new coordinator: {e}")

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
                # Notify coordinators and admins about new student registration
                try:
                    from django.db.models import Q
                    staff = User.objects.filter(
                        Q(role='coordinator', is_active=True) | Q(role='admin', is_active=True)
                    )
                    for staff_user in staff:
                        create_notification(
                            recipient=staff_user,
                            title='New Student Registration',
                            message=f'A new student ({user.get_full_name() or user.email}) has registered and is pending approval.',
                            type='general',
                            related_object=user,
                            related_object_type='student_registration',
                        )
                    broadcast_dashboard_update(section='students')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to notify coordinators about new student registration: {e}")

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
        """Get list of active courses for registration forms (cached 5min)."""
        try:
            course_list = cache.get('active_courses')
        except ConnectionError:
            course_list = None
        if course_list is None:
            courses = Course.objects.filter(is_active=True).order_by('name')
            course_list = [{'id': str(c.id), 'name': c.name} for c in courses]
            try:
                cache.set('active_courses', course_list, 300)
            except ConnectionError:
                pass
        return Response(course_list)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def send_otp(self, request):
        """Send OTP for password reset."""
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp_record = PasswordResetOTP.generate_otp(email)
            html_message = render_to_string('emails/otp_email.html', {
                'otp': otp_record.otp,
                'subject': 'Your OTP for Password Reset',
            })
            send_mail(
                subject='Your OTP for Password Reset',
                message=f'Your OTP is: {otp_record.otp}\n\nThis code will expire in 15 minutes.',
                html_message=html_message,
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
