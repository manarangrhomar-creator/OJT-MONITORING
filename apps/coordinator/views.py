from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import OJTProgram, OJTApplication, Attendance, NarrativeReport
from .serializers import OJTProgramSerializer, OJTApplicationSerializer, AttendanceSerializer, NarrativeReportSerializer


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
    
    @action(detail=False, methods=['get'])
    def my_students(self, request):
        """Get all students in coordinator's programs."""
        coordinator = request.user
        applications = OJTApplication.objects.filter(
            program__coordinator=coordinator
        ).select_related('student', 'program').order_by('-created_at')
        
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
    
    @action(detail=False, methods=['post'])
    def approve_student(self, request):
        """Approve a student application."""
        app_id = request.data.get('app_id')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'approved'
        application.approved_date = timezone.now()
        application.save()
        
        return Response({'message': 'Student approved successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def reject_student(self, request):
        """Reject a student application."""
        app_id = request.data.get('app_id')
        reason = request.data.get('reason', '')
        application = get_object_or_404(OJTApplication, id=app_id, program__coordinator=request.user)
        
        application.status = 'rejected'
        application.rejection_reason = reason
        application.save()
        
        return Response({'message': 'Student rejected'}, status=status.HTTP_200_OK)


class NarrativeReportViewSet(viewsets.ModelViewSet):
    """ViewSet for Narrative Report management."""
    serializer_class = NarrativeReportSerializer
    permission_classes = [IsCoordinator]
    
    def get_queryset(self):
        """Filter reports by coordinator's programs."""
        coordinator = self.request.user
        return NarrativeReport.objects.filter(
            program__coordinator=coordinator
        ).select_related('student', 'program')
    
    @action(detail=False, methods=['get'])
    def student_reports(self, request):
        """Get all narrative reports for a specific student."""
        student_id = request.query_params.get('student_id')
        program_id = request.query_params.get('program_id')
        
        if not student_id or not program_id:
            return Response({'error': 'student_id and program_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        reports = self.get_queryset().filter(
            student_id=student_id,
            program_id=program_id
        ).order_by('-report_date')
        
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)
