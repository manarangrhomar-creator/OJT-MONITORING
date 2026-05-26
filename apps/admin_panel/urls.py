from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminDashboardViewSet, UserManagementViewSet

router = DefaultRouter()
router.register(r'dashboard', AdminDashboardViewSet, basename='admin-dashboard')
router.register(r'users', UserManagementViewSet, basename='user-management')

urlpatterns = [
    path('', include(router.urls)),
]
