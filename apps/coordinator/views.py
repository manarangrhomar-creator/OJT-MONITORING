from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from apps.core.models import User
from apps.student.models import StudentNarrativeReport
from apps.student.serializers import StudentNarrativeReportSerializer
from .models import OJTProgram, OJTApplication, Attendance, SiteAssignment
from .serializers import OJTProgramSerializer, OJTApplicationSerializer, AttendanceSerializer, SiteAssignmentSerializer


class IsCoordinator(permissions.BasePermission):
    """Permission check for coordinators."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_coordinator()


class OJTProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for OJT Program management."""
    serializer_class = OJTProgramSerializer
    permission_classes = [IsCoordinator]
    filterset_fields = ['status']
    search_fields = ['name']
    
    def get_queryset(self):
        """Filter programs by coordinator."""
        user = self.request.user
        if user.is_admin():
            return OJTProgram.objects.all()
        return OJTProgram.objects.filter(coordinator=user)
    
    def perform_create(self, serializer):
        """Set coordinator to current user on creation."""
        serializer.save(coordinator=self.request.user, created_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get all applications for a program."""
        program = self.get_object()
        applications = program.applications.all()
        serializer = OJTApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class OJTApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for OJT Application management."""
    queryset = OJTApplication.objects.all()
    serializer_class = OJTApplicationSerializer
    permission_classes = [IsCoordinator]
    filterset_fields = ['status', 'program']
    search_fields = ['student__username', 'program__name']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an application."""
        application = self.get_object()
        application.status = 'approved'
        application.approved_date = timezone.now()
        application.save()
        return Response({'message': 'Application approved'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an application."""
        application = self.get_object()
        application.status = 'rejected'
        application.rejection_reason = request.data.get('reason', '')
        application.save()
        return Response({'message': 'Application rejected'}, status=status.HTTP_200_OK)


class AttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for Attendance management."""
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsCoordinator]
    filterset_fields = ['program', 'student', 'date']
    search_fields = ['student__username']
    
    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        """Clock in for attendance."""
        student_id = request.data.get('student_id')
        program_id = request.data.get('program_id')
        
        attendance, created = Attendance.objects.get_or_create(
            student_id=student_id,
            program_id=program_id,
            date=timezone.now().date(),
            defaults={'time_in': timezone.now().time()}
        )
        
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def clock_out(self, request, pk=None):
        """Clock out for attendance."""
        attendance = self.get_object()
        attendance.time_out = timezone.now().time()
        attendance.save()
        
        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CoordinatorDashboardViewSet(viewsets.ViewSet):
    """ViewSet for coordinator dashboard operations."""
    permission_classes = [IsCoordinator]
    
    @action(detail=False, methods=['get'], url_path='my-students')
    def my_students(self, request):
        """Get all students in coordinator's programs, filtered by course."""
        coordinator = request.user
        applications = OJTApplication.objects.filter(
            program__coordinator=coordinator
        ).select_related('student', 'program').order_by('-created_at')
        
        coordinator_course = coordinator.course
        if coordinator_course:
            applications = applications.filter(
                student__student_profile__course=coordinator_course
            )
        
        # Build student data with program info
        students_data = []
        for app in applications:
            student = app.student
            students_data.append({
                'id': student.id,
                'app_id': app.id,
                'name': student.get_full_name(),
                'email': student.email,
                'username': student.username,
                'program': app.program.name,
                'program_id': app.program.id,
                'status': app.status,
                'application_date': app.created_at,
                'approval_date': app.approved_date,
            })
        
        return Response(students_data)
    
    @action(detail=False, methods=['get'], url_path='student-accounts')
    def student_accounts(self, request):
        """Get all student accounts (role='student')."""
        students = User.objects.filter(role='student').order_by('-created_at')
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.email,
                'username': student.username,
                'is_active': student.is_active,
                'created_at': student.created_at,
            })
        return Response(students_data)

    @action(detail=False, methods=['post'], url_path='approve-student')
    def approve_student(self, request):
        """Approve a student application."""
        app_id = request.data.get('app_id')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'approved'
        application.approved_date = timezone.now()
        application.save()
        
        return Response({'message': 'Student approved successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='reject-student')
    def reject_student(self, request):
        """Reject a student application."""
        app_id = request.data.get('app_id')
        reason = request.data.get('reason', '')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'rejected'
        application.rejection_reason = reason
        application.save()
        
        return Response({'message': 'Student rejected'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='attendance-records')
    def attendance_records(self, request):
        """Get attendance records for coordinator's students."""
        coordinator = request.user
        program_id = request.query_params.get('program_id')
        student_id = request.query_params.get('student_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        programs = OJTProgram.objects.filter(coordinator=coordinator)
        if program_id:
            programs = programs.filter(id=program_id)

        attendances = Attendance.objects.filter(
            program__in=programs
        ).select_related('student', 'program').order_by('-date', 'time_in')

        if student_id:
            attendances = attendances.filter(student_id=student_id)
        if date_from:
            attendances = attendances.filter(date__gte=date_from)
        if date_to:
            attendances = attendances.filter(date__lte=date_to)

        records = []
        for att in attendances:
            records.append({
                'id': att.id,
                'student_id': att.student.id,
                'student_name': att.student.get_full_name(),
                'program_id': att.program.id,
                'program_name': att.program.name,
                'date': att.date,
                'time_in': str(att.time_in)[:5] if att.time_in else '—',
                'time_out': str(att.time_out)[:5] if att.time_out else '—',
                'status': 'Completed' if att.time_out else 'Pending',
                'facial_recognition_used': att.facial_recognition_used,
                'notes': att.notes,
            })

        return Response(records)

    @action(detail=False, methods=['get'], url_path='student-narratives')
    def student_narratives(self, request):
        """Get student-submitted narratives filtered by coordinator's course."""
        coordinator = request.user

        # Get approved students in coordinator's programs
        applications = OJTApplication.objects.filter(
            program__coordinator=coordinator,
            status='approved'
        ).select_related('student', 'program')

        coordinator_course = coordinator.course
        if coordinator_course:
            applications = applications.filter(
                student__student_profile__course=coordinator_course
            )

        student_ids = applications.values_list('student_id', flat=True)

        narratives = StudentNarrativeReport.objects.filter(
            student_id__in=student_ids
        ).select_related('student', 'program').order_by('-log_date')

        serializer = StudentNarrativeReportSerializer(narratives, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='grade-narrative')
    def grade_narrative(self, request):
        """Grade a student narrative report."""
        narrative_id = request.data.get('narrative_id')
        grade = request.data.get('grade')
        feedback = request.data.get('feedback', '')

        if not narrative_id:
            return Response({'error': 'narrative_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        if grade is None or not isinstance(grade, int) or grade < 1 or grade > 100:
            return Response({'error': 'Grade must be an integer between 1 and 100'}, status=status.HTTP_400_BAD_REQUEST)

        narrative = get_object_or_404(StudentNarrativeReport, id=narrative_id)
        narrative.grade = grade
        narrative.feedback = feedback
        narrative.graded_by = request.user
        narrative.graded_at = timezone.now()
        narrative.save(update_fields=['grade', 'feedback', 'graded_by', 'graded_at'])

        serializer = StudentNarrativeReportSerializer(narrative)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='pending-student-approvals')
    def pending_student_approvals(self, request):
        """Get students pending approval, filtered by coordinator's course."""
        coordinator = request.user
        students = User.objects.filter(
            role='student',
            approval_status='pending'
        ).select_related('student_profile').order_by('-created_at')

        coordinator_course = coordinator.course
        if coordinator_course:
            students = students.filter(student_profile__course=coordinator_course)

        data = []
        for s in students:
            course = ''
            try:
                course = s.student_profile.course
            except:
                pass
            data.append({
                'id': s.id,
                'name': s.get_full_name(),
                'email': s.email,
                'username': s.username,
                'course': course,
                'registration_date': s.created_at,
            })
        return Response(data)

    @action(detail=False, methods=['post'], url_path='approve-student-account')
    def approve_student_account(self, request):
        """Approve a student account."""
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(User, id=student_id, role='student')
        student.approval_status = 'approved'
        student.save(update_fields=['approval_status'])
        return Response({'message': 'Student account approved successfully'})

    @action(detail=False, methods=['post'], url_path='reject-student-account')
    def reject_student_account(self, request):
        """Reject a student account."""
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'error': 'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(User, id=student_id, role='student')
        student.approval_status = 'rejected'
        student.save(update_fields=['approval_status'])
        return Response({'message': 'Student account rejected'})


class SiteAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Site Assignment management."""
    serializer_class = SiteAssignmentSerializer
    permission_classes = [IsCoordinator]

    def get_queryset(self):
        coordinator = self.request.user
        return SiteAssignment.objects.filter(
            program__coordinator=coordinator
        ).select_related('student', 'program')

    @action(detail=False, methods=['get'], url_path='by-student')
    def by_student(self, request):
        """Get site assignment for a specific student."""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'error': 'student_id required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = self.get_queryset().get(student_id=student_id)
            serializer = self.get_serializer(assignment)
            return Response(serializer.data)
        except SiteAssignment.DoesNotExist:
            return Response({'error': 'No assignment found'}, status=status.HTTP_404_NOT_FOUND)
