from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OJTProgramViewSet, OJTApplicationViewSet, AttendanceViewSet, CoordinatorDashboardViewSet, NarrativeReportViewSet

router = DefaultRouter()
router.register(r'programs', OJTProgramViewSet, basename='ojt-program')
router.register(r'applications', OJTApplicationViewSet, basename='ojt-application')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'dashboard', CoordinatorDashboardViewSet, basename='coordinator-dashboard')
router.register(r'narrative-reports', NarrativeReportViewSet, basename='narrative-report')

urlpatterns = [
    path('', include(router.urls)),
]
