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
                return redirect('login')

            if request.user.role not in required_roles:
                return HttpResponseForbidden('Access Denied: You do not have permission to view this page.')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required(login_url='login')
@role_required('admin')
def admin_dashboard(request):
    """Admin dashboard view."""
    user = request.user
    initials = (user.first_name[0] if user.first_name else user.username[0]).upper()
    return render(request, 'admin_dashboard.html', {
        'user_name': user.get_full_name() or user.username,
        'user_initials': initials,
    })


@login_required(login_url='login')
@role_required('student')
def student_dashboard(request):
    """Student dashboard view."""
    user = request.user
    initials = (user.first_name[0] if user.first_name else user.username[0]).upper()
    return render(request, 'student_dashboard.html', {
        'user_name': user.get_full_name() or user.username,
        'user_initials': initials,
    })


@login_required(login_url='login')
@role_required('coordinator')
def coordinator_dashboard(request):
    """Coordinator dashboard view."""
    user = request.user
    initials = (user.first_name[0] if user.first_name else user.username[0]).upper()
    return render(request, 'coordinator_dashboard.html', {
        'user_name': user.get_full_name() or user.username,
        'user_initials': initials,
    })


def logout_view(request):
    """Logout user and clear authentication token."""
    if hasattr(request.user, 'auth_token'):
        request.user.auth_token.delete()
    
    logout(request)
    return redirect('home')
