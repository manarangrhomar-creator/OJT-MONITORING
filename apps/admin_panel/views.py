from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.core.models import User
from .models import SystemLog
from .serializers import AdminUserSerializer, SystemLogSerializer


class IsAdminUser(permissions.BasePermission):
    """Permission check for admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class AdminDashboardViewSet(viewsets.ViewSet):
    """ViewSet for admin dashboard operations."""
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=["get"])
    def dashboard_stats(self, request):
        """Get dashboard statistics."""
        total_users = User.objects.count()
        total_students = User.objects.filter(role="student").count()
        total_coordinators = User.objects.filter(role="coordinator").count()
        total_admins = User.objects.filter(role="admin").count()
        
        return Response({
            "total_users": total_users,
            "total_students": total_students,
            "total_coordinators": total_coordinators,
            "total_admins": total_admins,
        })
    
    @action(detail=False, methods=["get"])
    def students(self, request):
        """Get all OJT student accounts."""
        students = User.objects.filter(role="student").order_by("-created_at")
        serializer = AdminUserSerializer(students, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"])
    def coordinators(self, request):
        """Get all OJT coordinator accounts."""
        coordinators = User.objects.filter(role="coordinator").order_by("-created_at")
        serializer = AdminUserSerializer(coordinators, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="coordinator-approvals")
    def coordinator_approvals(self, request):
        """Get all OJT coordinator accounts with approval statuses."""
        coordinators = User.objects.filter(role="coordinator").order_by("-created_at")
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

        serializer = AdminUserSerializer(coordinator)
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"])
    def system_logs(self, request):
        """Get system logs."""
        logs = SystemLog.objects.all()[:100]
        serializer = SystemLogSerializer(logs, many=True)
        return Response(serializer.data)


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for user management."""
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete user by marking as inactive."""
        user = self.get_object()
        user.is_active = False
        user.save()
        
        # Log the activity
        SystemLog.objects.create(
            activity_type="user_deleted",
            description=f"User {user.username} deactivated",
            admin_user=request.user,
        )
        
        return Response({"message": "User deactivated successfully"}, status=status.HTTP_200_OK)