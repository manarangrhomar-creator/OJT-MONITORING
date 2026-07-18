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
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.views.generic import RedirectView, TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.core.dashboard_views import admin_dashboard, student_dashboard, coordinator_dashboard, logout_view
import os


def service_worker_view(request):
    """Serve the service worker from the root scope."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    return HttpResponse(content, content_type='application/javascript', headers={
        'Service-Worker-Allowed': '/',
        'Cache-Control': 'no-cache',
    })


def serve_protected_media(request, path):
    """
    Serve media files only to authenticated users.
    Returns 403 for unauthenticated requests, 404 for missing files.
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Authentication required to access media files.')
    
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponse('File not found', status=404)
    
    return FileResponse(open(file_path, 'rb'))

urlpatterns = [
    # Root URL - redirect to home
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # PWA - Service worker at root scope
    path('sw.js', service_worker_view, name='service-worker'),

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
    path('student/attendance/', TemplateView.as_view(template_name='facial.html'), name='student-attendance'),
    
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

# Serve media files in development (with authentication protection)
if settings.DEBUG:
    # Use protected media view instead of static() to require authentication
    media_url = settings.MEDIA_URL.rstrip('/')
    urlpatterns += [
        path(f'{media_url}/<path:path>', serve_protected_media, name='protected-media'),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
