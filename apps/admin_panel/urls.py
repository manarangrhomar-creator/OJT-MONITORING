from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminDashboardViewSet, UserManagementViewSet, CoursesViewSet, SitesViewSet

router = DefaultRouter()
router.register(r"dashboard", AdminDashboardViewSet, basename="admin-dashboard")
router.register(r"users", UserManagementViewSet, basename="user-management")
router.register(r"courses", CoursesViewSet, basename="admin-courses")
router.register(r"sites", SitesViewSet, basename="admin-sites")

urlpatterns = [
    path("dashboard/coordinators/<uuid:pk>/set-coordinator-approval/", AdminDashboardViewSet.as_view({"post": "set_coordinator_approval"}), name="set-coordinator-approval"),
    path("", include(router.urls)),
]
