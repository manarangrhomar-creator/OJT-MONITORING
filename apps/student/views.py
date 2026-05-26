from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.coordinator.models import OJTApplication, Attendance
from apps.coordinator.serializers import OJTApplicationSerializer, AttendanceSerializer
from .models import StudentProfile, FacialRecognition
from .serializers import StudentProfileSerializer, FacialRecognitionSerializer


class IsStudent(permissions.BasePermission):
    """Permission check for students."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_student()


class StudentProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for Student Profile management."""
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsStudent]
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current student's profile."""
        try:
            profile = StudentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Update student profile."""
        try:
            profile = StudentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


class StudentDashboardViewSet(viewsets.ViewSet):
    """ViewSet for student dashboard."""
    permission_classes = [IsStudent]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get student dashboard data."""
        student = request.user
        
        # Get applications
        applications = OJTApplication.objects.filter(student=student)
        approved_apps = applications.filter(status='approved').count()
        pending_apps = applications.filter(status='pending').count()
        
        # Get attendance
        attendances = Attendance.objects.filter(student=student)
        total_hours = sum(
            (att.time_out.hour - att.time_in.hour) if att.time_out else 0
            for att in attendances
        )
        
        return Response({
            'student_name': student.get_full_name(),
            'approved_applications': approved_apps,
            'pending_applications': pending_apps,
            'total_attendance_records': attendances.count(),
            'total_hours': total_hours,
        })
    
    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get student's OJT applications."""
        applications = OJTApplication.objects.filter(student=request.user)
        serializer = OJTApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_attendance(self, request):
        """Get student's attendance records."""
        attendances = Attendance.objects.filter(student=request.user).order_by('-date')
        serializer = AttendanceSerializer(attendances, many=True)
        return Response(serializer.data)


class FacialRecognitionViewSet(viewsets.ModelViewSet):
    """ViewSet for Facial Recognition management."""
    queryset = FacialRecognition.objects.all()
    serializer_class = FacialRecognitionSerializer
    permission_classes = [IsStudent]
    
    @action(detail=False, methods=['post'])
    def enroll_face(self, request):
        """Enroll facial data for student."""
        student = request.user
        facial_image = request.FILES.get('image')
        
        if not facial_image:
            return Response({'error': 'Image is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process facial data (placeholder for actual face encoding)
        facial_data, created = FacialRecognition.objects.get_or_create(
            student=student,
            defaults={
                'facial_encoding': b'placeholder',  # In production, use face_recognition library
                'is_verified': False
            }
        )
        
        serializer = self.get_serializer(facial_data)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verify_face(self, request):
        """Verify student using facial recognition."""
        student = request.user
        facial_image = request.FILES.get('image')
        
        if not facial_image:
            return Response({'error': 'Image is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            facial_data = FacialRecognition.objects.get(student=student)
            # In production, compare facial encodings here
            facial_data.is_verified = True
            facial_data.verification_date = timezone.now()
            facial_data.save()
            
            serializer = self.get_serializer(facial_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'Facial data not enrolled'}, status=status.HTTP_404_NOT_FOUND)
