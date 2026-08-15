import logging
import math
import cv2
import numpy as np
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import ValidationError
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from datetime import datetime, timedelta
from django.db.models import Q, Count, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.coordinator.models import OJTApplication, Attendance, OJTProgram, Site, SiteAssignment
from apps.coordinator.serializers import OJTApplicationSerializer, AttendanceSerializer
from apps.core.models import Notification
from apps.core.utils import create_and_send_notification, send_unread_count_update, broadcast_dashboard_update
from .models import StudentProfile, FacialRecognition, StudentNarrativeReport
from .serializers import (StudentProfileSerializer, FacialRecognitionSerializer,
                          StudentNarrativeReportSerializer, StudentProgramSerializer,
                          StudentApplySerializer)
from .face_utils import detect_face, encode_face, decode_face, verify_faces

logger = logging.getLogger(__name__)

GEOFENCE_RADIUS_METERS = 50


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates using Haversine formula."""
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class IsStudent(permissions.BasePermission):
    """Permission check for students."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_student()

    def has_object_permission(self, request, view, obj):
        """Defense-in-depth: ensure students can only access their own objects."""
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'student'):
            return obj.student == request.user
        return False


class StudentProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for Student Profile management."""
    serializer_class = StudentProfileSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return StudentProfile.objects.filter(user=self.request.user)
    
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
    throttle_classes = [UserRateThrottle]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get student dashboard data."""
        student = request.user
        
        # Get applications
        app_counts = OJTApplication.objects.filter(student=student).aggregate(
            approved=Count('id', filter=Q(status='approved')),
            pending=Count('id', filter=Q(status='pending')),
        )
        approved_apps = app_counts['approved']
        pending_apps = app_counts['pending']
        
        # Get attendance
        attendances = Attendance.objects.filter(student=student)
        total_duration = timedelta()
        for att in attendances:
            if att.time_out:
                t_in = datetime.combine(att.date, att.time_in)
                t_out = datetime.combine(att.date, att.time_out)
                if t_out < t_in:
                    t_out += timedelta(days=1)
                total_duration += (t_out - t_in)
        total_hours = total_duration.total_seconds() / 3600
        
        # Get profile info
        try:
            profile = StudentProfile.objects.get(user=student)
            student_id = profile.student_id
            course_name = profile.course.name if profile.course else ''
        except StudentProfile.DoesNotExist:
            student_id = ''
            course_name = ''

        return Response({
            'student_name': student.get_full_name(),
            'student_id': student_id,
            'course': course_name,
            'approved_applications': approved_apps,
            'pending_applications': pending_apps,
            'total_attendance_records': attendances.count(),
            'total_hours': total_hours,
            'created_at': student.created_at,
        })
    
    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get student's OJT applications."""
        applications = OJTApplication.objects.filter(student=request.user).select_related('student', 'program')
        serializer = OJTApplicationSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_attendance(self, request):
        """Get student's attendance records."""
        attendances = Attendance.objects.filter(student=request.user).select_related('student').order_by('-date')
        serializer = AttendanceSerializer(attendances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def today_status(self, request):
        """Check if student has clocked in/out today."""
        student = request.user
        today = timezone.now().date()
        try:
            attendance = Attendance.objects.get(student=student, date=today)
            return Response({
                'clocked_in': True,
                'clocked_out': attendance.time_out is not None,
                'time_in': str(attendance.time_in)[:5] if attendance.time_in else None,
                'time_out': str(attendance.time_out)[:5] if attendance.time_out else None,
            })
        except Attendance.DoesNotExist:
            return Response({
                'clocked_in': False,
                'clocked_out': False,
                'time_in': None,
                'time_out': None,
            })

    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Student clock in using facial recognition."""
        student = request.user
        facial_image = request.FILES.get('image')

        if not facial_image:
            return Response({'error': 'Image is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            facial_data = FacialRecognition.objects.get(student=student)
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'Facial data not enrolled. Please enroll your face first.'}, status=status.HTTP_404_NOT_FOUND)

        image_bytes = facial_image.read()
        embedding, _, face_count = detect_face(image_bytes)
        if embedding is None:
            return Response({'error': 'No face detected in the image.'}, status=status.HTTP_400_BAD_REQUEST)
        if face_count > 1:
            return Response({
                'error': 'Multiple faces detected in the image. Please ensure only your face is visible.'
            }, status=status.HTTP_400_BAD_REQUEST)

        is_match, confidence = verify_faces(facial_data.facial_encoding, embedding)
        if not is_match:
            return Response({
                'verified': False,
                'confidence': float(confidence),
                'error': 'Face does not match enrolled record'
            }, status=status.HTTP_403_FORBIDDEN)

        application = OJTApplication.objects.filter(
            student=student, status='approved'
        ).select_related('program', 'program__coordinator').first()
        if not application:
            return Response({'error': 'No approved OJT application found.'}, status=status.HTTP_400_BAD_REQUEST)

        # ── Geofence verification ──
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response(
                {'error': 'Location data is required. Please enable GPS and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        site_assignment = SiteAssignment.objects.filter(
            student=student, program=application.program
        ).select_related('site').first()

        if not site_assignment or not site_assignment.site:
            return Response(
                {'error': 'No site assigned. Please contact your coordinator.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        site = site_assignment.site
        if site.latitude is not None and site.longitude is not None:
            distance = haversine_distance(latitude, longitude, site.latitude, site.longitude)
            if distance > GEOFENCE_RADIUS_METERS:
                return Response(
                    {'error': 'You are not on site. Please go to your assigned work site and try again.'},
                    status=status.HTTP_403_FORBIDDEN
                )



        today = timezone.now().date()
        now_time = timezone.localtime(timezone.now()).time()

        attendance, created = Attendance.objects.get_or_create(
            student=student,
            program=application.program,
            date=today,
            defaults={
                'time_in': now_time,
                'facial_recognition_used': True,
                'latitude': latitude,
                'longitude': longitude,
            }
        )

        if not created:
            return Response({'error': 'Already clocked in today.'}, status=status.HTTP_400_BAD_REQUEST)

        create_and_send_notification(
            recipient=application.program.coordinator,
            title='Student Clocked In',
            message=f'{student.get_full_name() or student.username} clocked in via facial recognition.',
            type='attendance_update',
            related_object=attendance,
            related_object_type='Attendance',
            email_subject='Student Attendance Update',
        )

        serializer = AttendanceSerializer(attendance)
        broadcast_dashboard_update('attendance', data={'action': 'create', 'item': serializer.data})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def clock_out(self, request):
        """Student clock out using facial recognition."""
        student = request.user
        facial_image = request.FILES.get('image')

        if not facial_image:
            return Response({'error': 'Image is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            facial_data = FacialRecognition.objects.get(student=student)
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'Facial data not enrolled.'}, status=status.HTTP_404_NOT_FOUND)

        image_bytes = facial_image.read()
        embedding, _, face_count = detect_face(image_bytes)
        if embedding is None:
            return Response({'error': 'No face detected.'}, status=status.HTTP_400_BAD_REQUEST)
        if face_count > 1:
            return Response({
                'error': 'Multiple faces detected in the image. Please ensure only your face is visible.'
            }, status=status.HTTP_400_BAD_REQUEST)

        is_match, confidence = verify_faces(facial_data.facial_encoding, embedding)
        if not is_match:
            return Response({
                'verified': False,
                'confidence': float(confidence),
                'error': 'Face does not match enrolled record'
            }, status=status.HTTP_403_FORBIDDEN)

        # ── Geofence verification ──
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response(
                {'error': 'Location data is required. Please enable GPS and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        application = OJTApplication.objects.filter(
            student=student, status='approved'
        ).select_related('program', 'program__coordinator').first()
        if not application:
            return Response({'error': 'No approved OJT application found.'}, status=status.HTTP_400_BAD_REQUEST)

        site_assignment = SiteAssignment.objects.filter(
            student=student, program=application.program
        ).select_related('site').first()

        if not site_assignment or not site_assignment.site:
            return Response(
                {'error': 'No site assigned. Please contact your coordinator.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        site = site_assignment.site
        if site.latitude is not None and site.longitude is not None:
            distance = haversine_distance(latitude, longitude, site.latitude, site.longitude)
            if distance > GEOFENCE_RADIUS_METERS:
                return Response(
                    {'error': 'You are not on site. Please go to your assigned work site and try again.'},
                    status=status.HTTP_403_FORBIDDEN
                )



        today = timezone.now().date()

        try:
            attendance = Attendance.objects.get(student=student, date=today, time_out__isnull=True)
        except Attendance.DoesNotExist:
            return Response({'error': 'No active attendance record found for today.'}, status=status.HTTP_404_NOT_FOUND)

        attendance.time_out = timezone.localtime(timezone.now()).time()
        attendance.facial_recognition_used = True
        attendance.save()

        if application:
            create_and_send_notification(
                recipient=application.program.coordinator,
                title='Student Clocked Out',
                message=f'{student.get_full_name() or student.username} clocked out via facial recognition.',
                type='attendance_update',
                related_object=attendance,
                related_object_type='Attendance',
                email_subject='Student Attendance Update',
            )

        serializer = AttendanceSerializer(attendance)
        broadcast_dashboard_update('attendance', data={'action': 'update', 'item': serializer.data})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def available_programs(self, request):
        """List active programs matching student's course with available slots."""
        student = request.user
        try:
            profile = StudentProfile.objects.get(user=student)
            student_course = profile.course
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)

        applied_programs = OJTApplication.objects.filter(student=student).exclude(status='rejected').values_list('program_id', flat=True)

        programs = OJTProgram.objects.filter(
            status='active',
            coordinator__course=student_course
        ).select_related('coordinator').exclude(
            id__in=applied_programs
        ).annotate(
            approved_count=Count('applications', filter=Q(applications__status='approved'))
        ).filter(
            approved_count__lt=F('max_students')
        )

        serializer = StudentProgramSerializer(programs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='available-sites')
    def available_sites(self, request):
        """List active sites for student to choose during application."""
        sites = Site.objects.filter(is_active=True).order_by('name')
        data = [{
            'id': str(s.id),
            'name': s.name,
            'supervisor_name': s.supervisor_name,
            'contact_number': s.contact_number,
            'course': s.course.name if s.course else None,
        } for s in sites]
        return Response(data)

    @action(detail=False, methods=['post'])
    def apply(self, request):
        """Student applies to an OJT program."""
        serializer = StudentApplySerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            program = serializer.validated_data['program']
            existing = OJTApplication.objects.filter(
                student=request.user, program=program
            ).first()
            if existing and existing.status == 'rejected':
                existing.status = 'pending'
                existing.application_letter = serializer.validated_data['application_letter']
                existing.resume = serializer.validated_data.get('resume', None)
                existing.preferred_site = serializer.validated_data.get('preferred_site', None)
                existing.rejection_reason = ''
                existing.approved_date = None
                existing.save()
                application = existing
                is_new = False
            else:
                application = OJTApplication.objects.create(
                    student=request.user,
                    program=program,
                    application_letter=serializer.validated_data['application_letter'],
                    resume=serializer.validated_data.get('resume', None),
                    preferred_site=serializer.validated_data.get('preferred_site', None),
                    status='pending',
                    created_by=request.user,
                    updated_by=request.user,
                )
                is_new = True

            # Enroll face if provided
            face_image = request.FILES.get('face_image')
            if face_image:
                try:
                    image_bytes = face_image.read()
                    embedding, _, face_count = detect_face(image_bytes)
                    if embedding is None:
                        return Response({
                            'error': 'No face detected in the image. Please ensure your face is clearly visible.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    if face_count > 1:
                        return Response({
                            'error': 'Multiple faces detected in the image. Please ensure only your face is visible.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    # Check if this face is already registered to another student
                    existing_faces = FacialRecognition.objects.exclude(student=request.user).select_related('student')
                    face_is_duplicate = False
                    for existing in existing_faces:
                        if existing.facial_encoding:
                            is_match, _ = verify_faces(existing.facial_encoding, embedding, threshold=0.55)
                            if is_match:
                                face_is_duplicate = True
                                break

                    if not face_is_duplicate:
                        encoded = encode_face(embedding)
                        facial_data, _ = FacialRecognition.objects.get_or_create(
                            student=request.user,
                            defaults={
                                'facial_encoding': encoded,
                                'is_verified': True,
                                'verification_date': timezone.now()
                            }
                        )
                        if not facial_data.is_verified:
                            facial_data.facial_encoding = encoded
                            facial_data.is_verified = True
                            facial_data.verification_date = timezone.now()
                            facial_data.save()
                except Exception as e:
                    logger.warning(f"Face enrollment failed during application: {e}")
                    return Response({
                        'error': 'Face enrollment failed. Please try again with a clearer image.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            coordinator = application.program.coordinator
            site_text = f' and wants to take their OJT at {application.preferred_site.name}' if application.preferred_site else ''
            create_and_send_notification(
                recipient=coordinator,
                title='New OJT Application' if is_new else 'Re-applied to OJT Program',
                message=f'{request.user.get_full_name() or request.user.username} has {"applied to" if is_new else "re-applied to"} {application.program.name}{site_text}.',
                type='application_update',
                related_object=application,
                related_object_type='OJTApplication',
                email_subject='New OJT Application Submitted' if is_new else 'Re-applied to OJT Program',
            )
            out_serializer = OJTApplicationSerializer(application)
            broadcast_dashboard_update('applications', data={'action': 'create', 'item': out_serializer.data})
            return Response(out_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentNarrativeViewSet(viewsets.ModelViewSet):
    """ViewSet for Student Narrative Report management."""
    serializer_class = StudentNarrativeReportSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return StudentNarrativeReport.objects.filter(student=self.request.user).select_related('program')

    def perform_create(self, serializer):
        program = OJTApplication.objects.filter(
            student=self.request.user, status='approved'
        ).first()
        instance = serializer.save(
            student=self.request.user,
            program=program.program if program else None
        )
        if instance.program and instance.program.coordinator:
            create_and_send_notification(
                recipient=instance.program.coordinator,
                title='New Narrative Report',
                message=f'{self.request.user.get_full_name() or self.request.user.username} has submitted a new narrative report for {instance.log_date}.',
                type='general',
                related_object=instance,
                related_object_type='StudentNarrativeReport',
                email_subject='New Narrative Report Submitted',
            )
        serializer = self.get_serializer(instance)
        broadcast_dashboard_update('reports', data={'action': 'create', 'item': serializer.data})

    def perform_update(self, serializer):
        if serializer.instance.grade is not None:
            raise ValidationError({'error': 'Cannot edit a report that has already been graded.'})
        serializer.save()

    @action(detail=False, methods=['post'], url_path='submit-with-photos')
    def submit_with_photos(self, request):
        """Submit a narrative report with optional photo uploads."""
        serializer = StudentNarrativeReportSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            program = OJTApplication.objects.filter(
                student=self.request.user, status='approved'
            ).first()
            instance = serializer.save(
                student=request.user,
                program=program.program if program else None
            )
            if instance.program and instance.program.coordinator:
                create_and_send_notification(
                    recipient=instance.program.coordinator,
                    title='New Narrative Report',
                    message=f'{request.user.get_full_name() or request.user.username} has submitted a new narrative report for {instance.log_date}.',
                    type='general',
                    related_object=instance,
                    related_object_type='StudentNarrativeReport',
                    email_subject='New Narrative Report Submitted',
                )
            broadcast_dashboard_update('reports', data={'action': 'create', 'item': serializer.data})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacialRecognitionViewSet(viewsets.ModelViewSet):
    """ViewSet for Facial Recognition management."""
    serializer_class = FacialRecognitionSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return FacialRecognition.objects.filter(student=self.request.user)
    
    @action(detail=False, methods=['post'])
    def enroll_face(self, request):
        """Enroll facial data for student. Accepts multiple images, averages encodings."""
        import numpy as np
        from .face_quality import quality_gate, check_liveness
        student = request.user

        # Step 1: Consent enforcement
        consent = request.data.get('consent_given', 'false')
        if consent != 'true':
            return Response({'error': 'Facial recognition consent is required to enroll.'}, status=status.HTTP_400_BAD_REQUEST)

        images = request.FILES.getlist('image')
        face_thumbnail = request.FILES.get('face_thumbnail')

        if not images:
            return Response({'error': 'At least one image is required'}, status=status.HTTP_400_BAD_REQUEST)

        encodings = []
        quality_scores = []
        best_score = 0
        first_image_bytes = None
        for facial_image in images:
            image_bytes = facial_image.read()
            if first_image_bytes is None:
                first_image_bytes = image_bytes

            # Step 3: Quality gate per image
            passed, quality = quality_gate(image_bytes)
            if not passed:
                return Response({
                    'error': f'Image quality too low: {"; ".join(quality["messages"])}',
                    'quality': quality,
                }, status=status.HTTP_400_BAD_REQUEST)

            embedding, face_img, face_count = detect_face(image_bytes)
            if embedding is not None:
                if face_count > 1:
                    return Response({
                        'error': 'Multiple faces detected in the image. Please ensure only your face is visible.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                encodings.append(embedding)
                quality_scores.append(quality['score'])
                best_score = max(best_score, quality['score'])

        if not encodings:
            return Response({'error': 'No face detected in any image. Please ensure your face is clearly visible.'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 3b: Intra-ensemble check — ensure encodings are consistent
        if len(encodings) >= 2:
            # Compute pairwise cosine similarities between all encodings
            similarities = []
            for i in range(len(encodings)):
                for j in range(i + 1, len(encodings)):
                    sim = np.dot(encodings[i], encodings[j]) / (
                        np.linalg.norm(encodings[i]) * np.linalg.norm(encodings[j])
                    )
                    similarities.append(sim)
            
            avg_similarity = np.mean(similarities)
            min_similarity = np.min(similarities)
            
            # If average similarity is too low, images may be of different people
            if avg_similarity < 0.6:
                return Response({
                    'error': 'Captured images appear to be of different people. Please ensure all images show the same face.',
                    'similarity': float(avg_similarity),
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If any pair is too dissimilar, reject that specific image
            if min_similarity < 0.4:
                return Response({
                    'error': 'One or more images do not match the others. Please recapture all images.',
                    'min_similarity': float(min_similarity),
                }, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Liveness check — use the first detected face image
        liveness_passed, liveness_msg = check_liveness(first_image_bytes)
        if not liveness_passed:
            return Response({
                'error': f'Liveness check failed: {liveness_msg}',
                'liveness': {'passed': liveness_passed, 'message': liveness_msg},
            }, status=status.HTTP_400_BAD_REQUEST)

        # Step 5: Weighted average — weight by quality score for better accuracy
        # If we have quality scores, use them; otherwise fall back to simple average
        if 'quality_scores' in locals() and len(quality_scores) == len(encodings):
            # Normalize quality scores to weights
            weights = np.array(quality_scores, dtype=np.float64)
            weights = weights / weights.sum()
            # Weighted average
            avg_encoding = np.zeros_like(encodings[0], dtype=np.float64)
            for enc, weight in zip(encodings, weights):
                avg_encoding += enc * weight
            avg_encoding = avg_encoding.astype(np.float32)
        else:
            # Simple average fallback
            avg_encoding = np.mean(encodings, axis=0).astype(np.float32)

        # Step 6: Enrollment self-test — verify average encoding against original images
        self_test_passed = 0
        self_test_total = len(encodings)
        for enc in encodings:
            is_match, similarity = verify_faces(avg_encoding, enc, threshold=0.55)
            if is_match:
                self_test_passed += 1
        
        # If less than 80% of images match the average, the average is poor quality
        if self_test_passed < self_test_total * 0.8:
            return Response({
                'error': 'Enrollment quality too low — the averaged face encoding does not match the captured images well enough. Please recapture.',
                'self_test_passed': self_test_passed,
                'self_test_total': self_test_total,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if this face is already registered to another student
        existing_faces = FacialRecognition.objects.exclude(student=student).select_related('student')
        for existing in existing_faces:
            if existing.facial_encoding:
                is_match, similarity = verify_faces(existing.facial_encoding, avg_encoding, threshold=0.55)
                if is_match:
                    other_name = existing.student.get_full_name() or existing.student.username
                    return Response({
                        'error': f'This face is already registered to another student ({other_name}). '
                                  'If you believe this is an error, please contact your coordinator.'
                    }, status=status.HTTP_409_CONFLICT)

        encoded = encode_face(avg_encoding)

        # Save optional face thumbnail for my_face endpoint
        thumb_bytes = None
        if face_thumbnail:
            thumb_bytes = face_thumbnail.read()

        facial_data, created = FacialRecognition.objects.get_or_create(
            student=student,
            defaults={
                'facial_encoding': encoded,
                'face_image': thumb_bytes,
                'is_verified': True,
                'verification_date': timezone.now(),
                'consent_given': True,
                'consent_date': timezone.now(),
                'quality_score': best_score,
                'liveness_confirmed': True,
            }
        )

        if not created:
            facial_data.facial_encoding = encoded
            if thumb_bytes:
                facial_data.face_image = thumb_bytes
            facial_data.is_verified = True
            facial_data.verification_date = timezone.now()
            facial_data.consent_given = True
            facial_data.consent_date = timezone.now()
            facial_data.quality_score = best_score
            facial_data.liveness_confirmed = True
            facial_data.save()

        serializer = self.get_serializer(facial_data)
        data = serializer.data
        data['student_name'] = student.get_full_name() or student.username
        data['faces_used'] = len(encodings)
        data['quality_score'] = best_score
        return Response(data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='check-face')
    def check_face(self, request):
        """Validate that an uploaded image contains a face. Does not save anything."""
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        image_bytes = image_file.read()
        embedding, bbox, face_count = detect_face(image_bytes)
        if embedding is None:
            return Response({'face_detected': False, 'error': 'No face detected in the image.'}, status=status.HTTP_200_OK)
        return Response({
            'face_detected': True,
            'bbox': bbox,
            'face_count': face_count,
            'multiple_faces_detected': face_count > 1,
            'error': 'Multiple faces detected. Please ensure only one person is in the frame.' if face_count > 1 else None,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='my-face')
    def my_face(self, request):
        """Return enrolled face image as PNG."""
        try:
            fr = FacialRecognition.objects.get(student=request.user)
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'No enrolled face found'}, status=status.HTTP_404_NOT_FOUND)
        if not fr.face_image:
            return Response({'error': 'No face image found'}, status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(bytes(fr.face_image), content_type='image/png')

    @action(detail=False, methods=['post'], url_path='delete-face')
    def delete_face(self, request):
        """Delete enrolled face data for student."""
        deleted, _ = FacialRecognition.objects.filter(student=request.user).delete()
        if deleted:
            return Response({'detail': 'Face data deleted.'}, status=status.HTTP_200_OK)
        return Response({'error': 'No face data to delete'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def verify_face(self, request):
        """Verify student using facial recognition."""
        from .face_quality import quality_gate
        student = request.user
        facial_image = request.FILES.get('image')

        if not facial_image:
            return Response({'error': 'Image is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            facial_data = FacialRecognition.objects.get(student=student)
        except FacialRecognition.DoesNotExist:
            return Response({'error': 'Facial data not enrolled. Please enroll your face first.'}, status=status.HTTP_404_NOT_FOUND)

        image_bytes = facial_image.read()

        # Reject blurry/dark images
        passed, quality = quality_gate(image_bytes)
        if not passed:
            return Response({
                'error': f'Image quality too low: {"; ".join(quality["messages"])}',
                'verified': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        embedding, _, face_count = detect_face(image_bytes)

        if embedding is None:
            return Response({'error': 'No face detected in the image. Please ensure your face is clearly visible.'}, status=status.HTTP_400_BAD_REQUEST)
        if face_count > 1:
            return Response({
                'error': 'Multiple faces detected in the image. Please ensure only your face is visible.',
                'verified': False,
            }, status=status.HTTP_400_BAD_REQUEST)

        is_match, confidence = verify_faces(facial_data.facial_encoding, embedding)

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


class StudentNotificationViewSet(viewsets.ViewSet):
    """ViewSet for student notifications."""
    permission_classes = [IsStudent]

    def list(self, request):
        """Get paginated notifications for the current student."""
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))
        total = notifications.count()
        notifications = notifications[offset:offset + limit]
        data = [{
            'id': str(n.id),
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'related_object_id': str(n.related_object_id) if n.related_object_id else None,
            'related_object_type': n.related_object_type,
        } for n in notifications]
        return Response({'results': data, 'has_more': offset + limit < total})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count."""
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        try:
            notification = Notification.objects.get(id=pk, recipient=request.user)
            notification.is_read = True
            notification.save()
            send_unread_count_update(request.user)
            return Response({'message': 'Notification marked as read'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        send_unread_count_update(request.user)
        return Response({'message': 'All notifications marked as read'})
