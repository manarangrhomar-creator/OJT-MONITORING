from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from rest_framework.authtoken.models import Token


def role_required(*required_roles):
    """Decorator to check if user has any of the required roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('coordinator-login')

            if request.user.role not in required_roles:
                return HttpResponseForbidden('Access Denied: You do not have permission to view this page.')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required(login_url='admin-login')
@role_required('admin')
def admin_dashboard(request):
    """Admin dashboard view."""
    return render(request, 'admin_dashboard.html')


@login_required(login_url='student-login')
@role_required('student')
def student_dashboard(request):
    """Student dashboard view."""
    return render(request, 'student_dashboard.html')


def logout_view(request):
    """Logout user and clear authentication token."""
    try:
        request.user.auth_token.delete()
    except:
        pass
    
    logout(request)
    return redirect('home')
