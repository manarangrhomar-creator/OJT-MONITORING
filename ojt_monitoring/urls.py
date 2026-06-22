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
from apps.core.dashboard_views import admin_dashboard, student_dashboard, coordinator_dashboard, logout_view

urlpatterns = [
    # Root URL - redirect to home
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Frontend Pages - MUST come before admin/
    # Authentication
    path('auth/login/', TemplateView.as_view(template_name='login.html'), name='login'),
    path('auth/admin/login/', RedirectView.as_view(pattern_name='login', permanent=True)),
    path('auth/coordinator/login/', RedirectView.as_view(pattern_name='login', permanent=True)),
    path('auth/coordinator/register/', TemplateView.as_view(template_name='coordinator_register.html'), name='coordinator-register'),
    path('auth/forgotpassword/', TemplateView.as_view(template_name='forgot_password.html'), name='forgotpassword'),
    path('auth/coordinator/forgotpassword/', RedirectView.as_view(pattern_name='forgotpassword', permanent=False), name='coordinator-forgotpassword'),
    path('auth/student/login/', RedirectView.as_view(pattern_name='login', permanent=True)),
    path('auth/student/register/', TemplateView.as_view(template_name='ojtstudent_register.html'), name='student-register'),
    path('auth/student/forgotpassword/', RedirectView.as_view(pattern_name='forgotpassword', permanent=False), name='student-forgotpassword'),
    path('auth/logout/', logout_view, name='logout'),
    
    # Dashboards - Protected by role-based access
    path('dashboard/admin/', admin_dashboard, name='admin-dashboard'),
    path('dashboard/coordinator/', coordinator_dashboard, name='coordinator-dashboard'),
    path('dashboard/student/', student_dashboard, name='student-dashboard'),
    path('dashboard/generic/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('dashboard/approval/', RedirectView.as_view(pattern_name='admin-dashboard', permanent=False), name='approval-dashboard'),
    
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
    path('api/', include('apps.core.notification_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
