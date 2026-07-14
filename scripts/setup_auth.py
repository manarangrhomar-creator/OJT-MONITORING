#!/usr/bin/env python
"""
Setup verification and testing script for OJT Monitoring authentication system
Run this after implementing the authentication system
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from django.conf import settings
from apps.core.models import User
from rest_framework.authtoken.models import Token

def create_test_users():
    """Create test users for each role."""
    import secrets
    default_pw = secrets.token_urlsafe(12)
    test_data = [
        {
            'username': 'admin_test',
            'email': 'admin@isu.edu.ph',
            'password': os.environ.get('ADMIN_TEST_PASSWORD', default_pw),
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'admin'
        },
        {
            'username': 'coordinator_test',
            'email': 'coordinator@isu.edu.ph',
            'password': os.environ.get('COORDINATOR_TEST_PASSWORD', default_pw),
            'first_name': 'Coordinator',
            'last_name': 'User',
            'role': 'coordinator'
        },
        {
            'username': 'student_test',
            'email': 'student@isu.edu.ph',
            'password': os.environ.get('STUDENT_TEST_PASSWORD', default_pw),
            'first_name': 'Student',
            'last_name': 'User',
            'role': 'student'
        }
    ]
    
    print("\n" + "="*60)
    print("CREATING TEST USERS FOR OJT MONITORING SYSTEM")
    print("="*60 + "\n")
    
    for data in test_data:
        username = data['username']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"✓ User '{username}' already exists")
            continue
        
        # Create user
        user = User.objects.create_user(**data)
        token, created = Token.objects.get_or_create(user=user)
        
        print(f"✓ Created {data['role'].upper()}: {username}")
        print(f"  Email: {data['email']}")
        print(f"  Password: {data['password']}")
        print(f"  Token: {token.key}\n")
    
    print("="*60)
    print("TEST USERS CREATED SUCCESSFULLY!")
    print("="*60 + "\n")


def verify_authentication_setup():
    """Verify that authentication is properly configured."""
    print("\n" + "="*60)
    print("VERIFYING AUTHENTICATION SETUP")
    print("="*60 + "\n")
    
    checks = []
    
    # Check if rest_framework.authtoken is installed
    if 'rest_framework.authtoken' in settings.INSTALLED_APPS:
        print("✓ rest_framework.authtoken is installed")
        checks.append(True)
    else:
        print("✗ rest_framework.authtoken is NOT installed")
        checks.append(False)
    
    # Check if TokenAuthentication is configured
    auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
    if 'rest_framework.authentication.TokenAuthentication' in auth_classes:
        print("✓ Token authentication is configured")
        checks.append(True)
    else:
        print("✗ Token authentication is NOT configured")
        checks.append(False)
    
    # Check Token model
    try:
        from rest_framework.authtoken.models import Token
        print("✓ Token model is available")
        checks.append(True)
    except:
        print("✗ Token model is NOT available")
        checks.append(False)
    
    # Check User model
    try:
        user_count = User.objects.count()
        print(f"✓ User model is available ({user_count} users in database)")
        checks.append(True)
    except:
        print("✗ User model is NOT available")
        checks.append(False)
    
    # Check dashboard views
    try:
        from apps.core.dashboard_views import admin_dashboard, coordinator_dashboard, student_dashboard
        print("✓ Dashboard protection views are available")
        checks.append(True)
    except:
        print("✗ Dashboard protection views are NOT available")
        checks.append(False)
    
    print("\n" + "="*60)
    if all(checks):
        print("✓ ALL CHECKS PASSED - SYSTEM IS READY!")
    else:
        print("✗ SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
    print("="*60 + "\n")


def print_test_credentials():
    """Print test credentials for manual testing."""
    print("\n" + "="*60)
    print("TEST CREDENTIALS FOR MANUAL TESTING")
    print("="*60 + "\n")
    
    users = User.objects.all()
    
    for user in users:
        try:
            token = Token.objects.get(user=user)
            print(f"Role: {user.get_role_display()}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Token: {token.key}")
            print()
        except Token.DoesNotExist:
            pass
    
    print("="*60)
    print("LOGIN ENDPOINTS")
    print("="*60)
    print("Admin:       http://localhost:8000/auth/admin/login/")
    print("Coordinator: http://localhost:8000/auth/coordinator/login/")
    print("Student:     http://localhost:8000/auth/student/login/")
    print("\n" + "="*60 + "\n")


if __name__ == '__main__':
    verify_authentication_setup()
    create_test_users()
    print_test_credentials()
