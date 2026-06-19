from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentProfileViewSet, StudentDashboardViewSet, StudentNarrativeViewSet, FacialRecognitionViewSet

router = DefaultRouter()
router.register(r'profile', StudentProfileViewSet, basename='student-profile')
router.register(r'dashboard', StudentDashboardViewSet, basename='student-dashboard')
router.register(r'narratives', StudentNarrativeViewSet, basename='student-narrative')
router.register(r'facial', FacialRecognitionViewSet, basename='facial-recognition')

urlpatterns = [
    path('', include(router.urls)),
]
