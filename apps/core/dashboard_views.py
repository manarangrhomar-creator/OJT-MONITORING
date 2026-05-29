from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from rest_framework.authtoken.models import Token


def role_required(required_role):
    """Decorator to check if user has the required role."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('coordinator-login')
            
            if request.user.role != required_role:
                return HttpResponseForbidden('Access Denied: You do not have permission to view this page.')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required(login_url='admin-login')
@role_required('admin')
def admin_dashboard(request):
    """Admin dashboard view."""
    return render(request, 'admin_dashboard.html')


@login_required(login_url='coordinator-login')
@role_required('coordinator')
def coordinator_dashboard(request):
    """Coordinator dashboard view."""
    return render(request, 'coordinator_dashboard.html')


@login_required(login_url='student-login')
@role_required('student')
def student_dashboard(request):
    """Student dashboard view."""
    return render(request, 'student_dashboard.html')


@login_required(login_url='admin-login')
@role_required('admin')
def approval_dashboard(request):
    """Approval dashboard view."""
    return render(request, 'approval_dashboard.html')


def logout_view(request):
    """Logout user and clear authentication token."""
    try:
        request.user.auth_token.delete()
    except:
        pass
    
    logout(request)
    return redirect('home')
