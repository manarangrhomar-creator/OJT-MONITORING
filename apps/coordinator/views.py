from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import OJTProgram, OJTApplication, Attendance
from .serializers import OJTProgramSerializer, OJTApplicationSerializer, AttendanceSerializer


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
