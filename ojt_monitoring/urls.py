"""
URL configuration for ojt_monitoring project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from . import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app import views
    2. Add a URL to urlpatterns:  path('', views.Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Root URL - redirect to home
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Frontend Pages - MUST come before admin/
    # Authentication
    path('auth/admin/login/', TemplateView.as_view(template_name='admin_login.html'), name='admin-login'),
    path('auth/coordinator/login/', TemplateView.as_view(template_name='coordinator_login.html'), name='coordinator-login'),
    path('auth/coordinator/register/', TemplateView.as_view(template_name='coordinator_register.html'), name='coordinator-register'),
    path('auth/student/login/', TemplateView.as_view(template_name='ojtstudent_login.html'), name='student-login'),
    path('auth/student/register/', TemplateView.as_view(template_name='ojtstudent_register.html'), name='student-register'),
    
    # Dashboards
    path('dashboard/admin/', TemplateView.as_view(template_name='admin_dashboard.html'), name='admin-dashboard'),
    path('dashboard/coordinator/', TemplateView.as_view(template_name='coordinator_dashboard.html'), name='coordinator-dashboard'),
    path('dashboard/student/', TemplateView.as_view(template_name='student_dashboard.html'), name='student-dashboard'),
    path('dashboard/generic/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('dashboard/approval/', TemplateView.as_view(template_name='approval_dashboard.html'), name='approval-dashboard'),
    
    # Student Facial Recognition
    path('student/facial/', TemplateView.as_view(template_name='ojtstudent_facial.html'), name='student-facial'),
    
    # Admin panel (Django built-in)
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # App URLs
    path('api/auth/', include('apps.authentication.urls')),
    path('api/admin/', include('apps.admin_panel.urls')),
    path('api/coordinator/', include('apps.coordinator.urls')),
    path('api/student/', include('apps.student.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
