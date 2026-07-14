from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from apps.core.models import User, Course
from apps.student.models import StudentProfile
from apps.core.utils import create_notification, broadcast_dashboard_update
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserSerializer, SendOTPSerializer, VerifyOTPSerializer, ResetPasswordSerializer
from .models import PasswordResetOTP, EmailVerificationToken, LoginAttempt
import os

RATE_LIMIT_MINUTES = 5
RATE_LIMIT_MAX = 10  # per-IP cap per window
LOCKOUT_MINUTES = 15
LOCKOUT_MAX_ATTEMPTS = 5  # lock account after 5 failed attempts


def _is_account_locked(user):
    """Check if user account is locked due to too many failed attempts."""
    cutoff = timezone.now() - timedelta(minutes=LOCKOUT_MINUTES)
    recent_failures = LoginAttempt.objects.filter(
        user=user, success=False, created_at__gte=cutoff
    ).count()
    return recent_failures >= LOCKOUT_MAX_ATTEMPTS


def _check_rate_limit(request, action_key):
    """Simple cache-based rate limit. Returns True if allowed."""
    ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    cache_key = f'rl:{action_key}:{ip}'
    count = cache.get(cache_key, 0)
    if count >= RATE_LIMIT_MAX:
        return False
    cache.set(cache_key, count + 1, RATE_LIMIT_MINUTES * 60)
    return True


def _log_failed_attempt(identifier, ip, user_agent):
    """Log a failed login attempt to the database."""
    user = None
    try:
        user = User.objects.get(email=identifier)
    except User.DoesNotExist:
        try:
            from apps.student.models import StudentProfile
            profile = StudentProfile.objects.get(student_id=identifier)
            user = profile.user
        except Exception:
            pass
    if user:
        LoginAttempt.objects.create(user=user, ip_address=ip, success=False, user_agent=user_agent)


def _attach_logo(email):
    """Attach the ISU logo as an inline image with Content-ID."""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'isu_new_seal_512x512.png')
    if os.path.exists(logo_path):
        from email.mime.image import MIMEImage
        with open(logo_path, 'rb') as f:
            img = MIMEImage(f.read(), _subtype='png')
            img.add_header('Content-ID', '<isu_logo>')
            img.add_header('Content-Disposition', 'inline', filename='isu_logo.png')
            email.attach(img)


class AuthenticationViewSet(viewsets.ViewSet):
    """ViewSet for authentication operations."""
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def register(self, request):
        """Register a new user."""
        if not _check_rate_limit(request, 'register'):
            return Response({'error': 'Too many requests. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        data = request.data.copy()
        data['role'] = 'student'  # ponytail: self-registration is always student; admin creates others
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

            # Generate email verification token for students
            if user.role == 'student':
                token_obj = EmailVerificationToken.generate(user)
                try:
                    verify_url = f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/api/auth/verify-email/?token={token_obj.token}"
                    from apps.core.tasks import send_email_task
                    send_email_task.delay(
                        recipient_email=user.email,
                        subject='Verify your email address',
                        title='Email Verification',
                        message=f'Please verify your email by clicking this link: {verify_url}\n\nThis link expires in 24 hours.',
                        recipient_name=user.get_full_name() or user.username,
                    )
                except Exception:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.exception('Failed to send verification email')

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
                    'message': 'Student account created successfully. Please wait for your admin to approve your account before logging in.',
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
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Check IP rate limit
        rl_key = f'rl:login:{ip}'
        if cache.get(rl_key, 0) >= RATE_LIMIT_MAX:
            return Response({'error': 'Too many requests. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        identifier = request.data.get('identifier', '')

        # Check account lockout before authenticating
        try:
            user_obj = User.objects.get(email=identifier)
            if _is_account_locked(user_obj):
                return Response(
                    {'error': f'Account locked due to too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.'},
                    status=status.HTTP_423_LOCKED
                )
        except User.DoesNotExist:
            pass

        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Check account lockout after user resolution
            if _is_account_locked(user):
                return Response(
                    {'error': f'Account locked due to too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.'},
                    status=status.HTTP_423_LOCKED
                )

            # Get or create token
            token, created = Token.objects.get_or_create(user=user)

            # Create Django session for @login_required views
            login(request, user)

            # Log successful attempt
            LoginAttempt.objects.create(user=user, ip_address=ip, success=True, user_agent=user_agent)

            response = Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_200_OK)

            # Set auth token in httpOnly cookie (not accessible via JavaScript)
            is_prod = not settings.DEBUG
            response.set_cookie(
                'auth_token',
                token.key,
                httponly=True,
                secure=is_prod,
                samesite='Lax',
                max_age=86400 * 7,  # 7 days
                path='/',
            )
            return response

        # Failed login — increment rate limit and log
        cache.set(rl_key, cache.get(rl_key, 0) + 1, RATE_LIMIT_MINUTES * 60)
        _log_failed_attempt(identifier, ip, user_agent)

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
        
        response = Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        # Clear the auth token cookie
        response.delete_cookie('auth_token', path='/')
        return response
    
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
        if not _check_rate_limit(request, 'otp'):
            return Response({'error': 'Too many requests. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email_addr = serializer.validated_data['email']
            otp_record = PasswordResetOTP.generate_otp(email_addr)
            html_message = render_to_string('emails/otp_email.html', {
                'otp': otp_record.otp,
                'subject': 'Your OTP for Password Reset',
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            })
            plain_message = f'Your OTP is: {otp_record.otp}\n\nThis code will expire in 15 minutes.'
            email = EmailMultiAlternatives(
                subject='Your OTP for Password Reset',
                body=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                to=[email_addr],
            )
            email.attach_alternative(html_message, 'text/html')
            _attach_logo(email)
            email.send(fail_silently=False)
            return Response({
                'message': 'OTP sent successfully',
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def verify_otp(self, request):
        """Verify OTP code."""
        if not _check_rate_limit(request, 'verify_otp'):
            return Response({'error': 'Too many requests. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response({'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def reset_password(self, request):
        """Reset password with OTP verification."""
        if not _check_rate_limit(request, 'reset'):
            return Response({'error': 'Too many requests. Try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
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

    @action(detail=False, methods=['get', 'post'], permission_classes=[AllowAny], authentication_classes=[])
    def verify_email(self, request):
        """Verify email with token (GET via link or POST with token)."""
        token_str = request.query_params.get('token') or request.data.get('token')
        if not token_str:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token_obj = EmailVerificationToken.objects.get(token=token_str)
        except EmailVerificationToken.DoesNotExist:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        if not token_obj.is_valid():
            return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
        token_obj.verified = True
        token_obj.save(update_fields=['verified'])
        return Response({'message': 'Email verified successfully'}, status=status.HTTP_200_OK)


