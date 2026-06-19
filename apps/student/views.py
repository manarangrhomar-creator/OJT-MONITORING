import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.coordinator.models import OJTApplication, Attendance
from apps.coordinator.serializers import OJTApplicationSerializer, AttendanceSerializer
from .models import StudentProfile, FacialRecognition, StudentNarrativeReport
from .serializers import StudentProfileSerializer, FacialRecognitionSerializer, StudentNarrativeReportSerializer
from .face_utils import detect_face, encode_face, verify_faces

logger = logging.getLogger(__name__)


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


class StudentNarrativeViewSet(viewsets.ModelViewSet):
    """ViewSet for Student Narrative Report management."""
    serializer_class = StudentNarrativeReportSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return StudentNarrativeReport.objects.filter(student=self.request.user).select_related('program')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=False, methods=['post'], url_path='submit-with-photos')
    def submit_with_photos(self, request):
        """Submit a narrative report with optional photo uploads."""
        serializer = StudentNarrativeReportSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(student=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        image_bytes = facial_image.read()
        face_roi, coords = detect_face(image_bytes)

        if face_roi is None:
            return Response({'error': 'No face detected in the image. Please ensure your face is clearly visible.'}, status=status.HTTP_400_BAD_REQUEST)

        encoding = encode_face(face_roi)

        facial_data, created = FacialRecognition.objects.get_or_create(
            student=student,
            defaults={
                'facial_encoding': encoding,
                'is_verified': True,
                'verification_date': timezone.now()
            }
        )

        if not created:
            facial_data.facial_encoding = encoding
            facial_data.is_verified = True
            facial_data.verification_date = timezone.now()
            facial_data.save()

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
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'Facial data not enrolled. Please enroll your face first.'}, status=status.HTTP_404_NOT_FOUND)

        image_bytes = facial_image.read()
        new_face_roi, coords = detect_face(image_bytes)

        if new_face_roi is None:
            return Response({'error': 'No face detected in the image. Please ensure your face is clearly visible.'}, status=status.HTTP_400_BAD_REQUEST)

        is_match, confidence = verify_faces(facial_data.facial_encoding, new_face_roi)

        if is_match:
            facial_data.is_verified = True
            facial_data.verification_date = timezone.now()
            facial_data.save()

            return Response({
                'verified': True,
                'confidence': float(confidence),
                'message': 'Face verified successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'verified': False,
                'confidence': float(confidence),
                'message': 'Face does not match enrolled record'
            }, status=status.HTTP_200_OK)
