from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from apps.core.models import User, Course
from apps.core.tasks import send_email_task
from apps.core.utils import broadcast_dashboard_update
from apps.coordinator.models import Site, OJTProgram, OJTApplication
from .models import SystemLog
from .serializers import (AdminUserSerializer, CourseSerializer, SiteSerializer,
                          SystemLogSerializer, AdminProgramSerializer,
                          AdminProgramStudentSerializer, CoordinatorChoiceSerializer)


class IsAdminUser(permissions.BasePermission):
    """Permission check for admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


def invalidate_system_logs_cache():
    cache.delete('admin_system_logs')


class AdminDashboardViewSet(viewsets.ViewSet):
    """ViewSet for admin dashboard operations."""
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=["get"])
    def dashboard_stats(self, request):
        """Get dashboard statistics (cached 60s)."""
        stats = cache.get('admin_dashboard_stats')
        if stats is None:
            stats = {
                "total_users": User.objects.count(),
                "total_students": User.objects.filter(role="student").count(),
                "total_coordinators": User.objects.filter(role="coordinator").count(),
                "total_admins": User.objects.filter(role="admin").count(),
            }
            cache.set('admin_dashboard_stats', stats, 60)
        return Response(stats)
    
    @action(detail=False, methods=["get"])
    def students(self, request):
        """Get only approved OJT student accounts for admin listing."""
        students = User.objects.filter(role="student", approval_status="approved").select_related('course').order_by("-created_at")
        serializer = AdminUserSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"])
    def coordinators(self, request):
        """Get all OJT coordinator accounts."""
        coordinators = User.objects.filter(role="coordinator").exclude(approval_status="pending").select_related('course').order_by("-created_at")
        serializer = AdminUserSerializer(coordinators, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], url_path="coordinator-approvals")
    def coordinator_approvals(self, request):
        """Get all OJT coordinator accounts with approval statuses."""
        coordinators = User.objects.filter(role="coordinator", approval_status="pending").select_related('course').order_by("-created_at")
        serializer = AdminUserSerializer(coordinators, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], url_path="set-coordinator-approval")
    def set_coordinator_approval(self, request, pk=None):
        """Update approval status for a coordinator account."""
        status_value = request.data.get("approval_status")
        if status_value not in ["pending", "approved", "rejected"]:
            return Response({"message": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        coordinator = get_object_or_404(User, id=pk, role="coordinator")
        coordinator.approval_status = status_value
        coordinator.save(update_fields=["approval_status"])

        SystemLog.objects.create(
            activity_type="approval_made",
            description=f"Coordinator {coordinator.username} status set to {status_value}",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()

        coordinator_name = coordinator.get_full_name() or coordinator.username
        if status_value == 'approved':
            send_email_task.delay(
                recipient_email=coordinator.email,
                subject='OJT Coordinator Account Approved',
                message='Your OJT coordinator account has been approved. You can now log in.',
                title='Account Approved',
                recipient_name=coordinator_name,
            )
        elif status_value == 'rejected':
            send_email_task.delay(
                recipient_email=coordinator.email,
                subject='OJT Coordinator Account Rejected',
                message='Your OJT coordinator account has been rejected. Please contact the administrator for further information.',
                recipient_name=coordinator_name,
            )
            coordinator.delete()
            broadcast_dashboard_update('coordinators', data={'action': 'delete'})
            return Response({"message": "Coordinator rejected and deleted permanently"})

        serializer = AdminUserSerializer(coordinator)
        broadcast_dashboard_update('coordinators', data={'action': 'update', 'item': serializer.data})
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], url_path="student-approvals")
    def student_approvals(self, request):
        """Get all pending student accounts for approval."""
        students = User.objects.filter(role="student", approval_status="pending").order_by("-created_at")
        serializer = AdminUserSerializer(students, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="approve-student")
    def approve_student(self, request, pk=None):
        """Approve a student account."""
        student = get_object_or_404(User, id=pk, role="student")
        student.approval_status = "approved"
        student.save(update_fields=["approval_status"])

        SystemLog.objects.create(
            activity_type="approval_made",
            description=f"Student {student.username} account approved",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()

        student_name = student.get_full_name() or student.username
        send_email_task.delay(
            recipient_email=student.email,
            subject="OJT Student Account Approved",
            message="Your OJT student account has been approved. You can now log in and apply for programs.",
            title="Account Approved",
            recipient_name=student_name,
        )
        serializer = AdminUserSerializer(student)
        broadcast_dashboard_update('students', data={'action': 'update', 'item': serializer.data})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="reject-student")
    def reject_student(self, request, pk=None):
        """Reject a student account."""
        student = get_object_or_404(User, id=pk, role="student")
        student.approval_status = "rejected"
        student.save(update_fields=["approval_status"])

        SystemLog.objects.create(
            activity_type="approval_made",
            description=f"Student {student.username} account rejected",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()

        student_name = student.get_full_name() or student.username
        send_email_task.delay(
            recipient_email=student.email,
            subject="OJT Student Account Rejected",
            message="Your OJT student account has been rejected. Please contact the administrator for further information.",
            recipient_name=student_name,
        )
        serializer = AdminUserSerializer(student)
        broadcast_dashboard_update('students', data={'action': 'update', 'item': serializer.data})
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def system_logs(self, request):
        """Get system logs (cached 60s)."""
        logs_data = cache.get('admin_system_logs')
        if logs_data is None:
            logs = SystemLog.objects.all().select_related('admin_user')[:100]
            serializer = SystemLogSerializer(logs, many=True)
            logs_data = serializer.data
            cache.set('admin_system_logs', logs_data, 60)
        return Response(logs_data)


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    
    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, *args, **kwargs):
        """Set user status to inactive (archive)."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        SystemLog.objects.create(
            activity_type="user_archived",
            description=f"User {user.username} archived (set to inactive)",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()
        
        return Response({"message": f"User {user.username} archived"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, *args, **kwargs):
        """Restore user to active status."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])

        SystemLog.objects.create(
            activity_type="user_restored",
            description=f"User {user.username} restored (set to active)",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()

        return Response({"message": f"User {user.username} restored"}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        SystemLog.objects.create(
            activity_type="user_deleted",
            description=f"User {instance.username} deleted",
            admin_user=self.request.user,
        )
        invalidate_system_logs_cache()
        instance.delete()


class CoursesViewSet(viewsets.ModelViewSet):
    """ViewSet for Course management."""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['name']
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        cache.delete('active_courses')

    def perform_update(self, serializer):
        serializer.save()
        cache.delete('active_courses')

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        course = self.get_object()
        course.is_active = False
        course.save(update_fields=['is_active'])
        cache.delete('active_courses')
        return Response({'message': 'Course archived successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, pk=None):
        course = self.get_object()
        course.is_active = True
        course.save(update_fields=['is_active'])
        cache.delete('active_courses')
        return Response({'message': 'Course restored successfully.'}, status=status.HTTP_200_OK)


class AdminProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for admin program management."""
    queryset = OJTProgram.objects.all().select_related('coordinator').order_by('-created_at')
    serializer_class = AdminProgramSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['name', 'coordinator__first_name', 'coordinator__last_name']
    filterset_fields = ['status']
    pagination_class = None

    def perform_create(self, serializer):
        program = serializer.save(created_by=self.request.user)
        SystemLog.objects.create(
            activity_type="program_created",
            description=f"Subject '{program.name}' created",
            admin_user=self.request.user,
        )
        invalidate_system_logs_cache()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        SystemLog.objects.create(
            activity_type="program_deleted",
            description=f"Subject '{instance.name}' deleted",
            admin_user=self.request.user,
        )
        invalidate_system_logs_cache()
        instance.delete()

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        program = self.get_object()
        program.status = 'inactive'
        program.save(update_fields=['status'])
        SystemLog.objects.create(
            activity_type="program_archived",
            description=f"Subject {program.name} archived",
            admin_user=self.request.user,
        )
        invalidate_system_logs_cache()
        return Response({'message': 'Subject archived successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, pk=None):
        program = self.get_object()
        program.status = 'active'
        program.save(update_fields=['status'])
        SystemLog.objects.create(
            activity_type="program_restored",
            description=f"Subject {program.name} restored",
            admin_user=request.user,
        )
        invalidate_system_logs_cache()
        return Response({'message': 'Subject restored successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get approved students in a program."""
        program = self.get_object()
        applications = OJTApplication.objects.filter(
            program=program, status='approved'
        ).select_related(
            'student', 'student__student_profile', 'student__student_profile__course'
        ).order_by('student__last_name')
        serializer = AdminProgramStudentSerializer(applications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def coordinator_choices(self, request):
        """Get approved coordinators for dropdown."""
        coordinators = User.objects.filter(
            role='coordinator', approval_status='approved', is_active=True
        ).select_related('course').order_by('first_name')
        serializer = CoordinatorChoiceSerializer(coordinators, many=True)
        return Response(serializer.data)


class SitesViewSet(viewsets.ModelViewSet):
    """ViewSet for Site management. Includes approve/reject for student-created sites."""
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [IsAdminUser]
    search_fields = ['name']
    filterset_fields = ['course', 'is_active', 'status']
    pagination_class = None

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # Admin editing a site can also adjust status if needed
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a pending student-created site."""
        site = self.get_object()
        if site.status != 'pending':
            return Response(
                {'error': f'Cannot approve a site that is already "{site.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        site.status = 'approved'
        site.save(update_fields=['status', 'updated_at'])
        return Response({'message': f'Site "{site.name}" approved.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Reject a pending student-created site with a reason."""
        site = self.get_object()
        if site.status != 'pending':
            return Response(
                {'error': f'Cannot reject a site that is already "{site.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('rejection_reason', '').strip()
        if not reason:
            return Response(
                {'error': 'rejection_reason is required when rejecting a site.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        site.status = 'rejected'
        site.rejection_reason = reason
        site.save(update_fields=['status', 'rejection_reason', 'updated_at'])
        return Response({'message': f'Site "{site.name}" rejected.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        site = self.get_object()
        site.is_active = False
        site.save(update_fields=['is_active'])
        return Response({'message': 'Site archived successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unarchive')
    def unarchive(self, request, pk=None):
        site = self.get_object()
        site.is_active = True
        site.save(update_fields=['is_active'])
        return Response({'message': 'Site restored successfully.'}, status=status.HTTP_200_OK)