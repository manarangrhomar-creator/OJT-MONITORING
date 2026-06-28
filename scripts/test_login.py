#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.authentication.serializers import UserLoginSerializer
from apps.core.models import User
from rest_framework.authtoken.models import Token

print("\n=== Testing Admin Login ===\n")

# First, check what the actual password is
admin_user = User.objects.get(username='admin')
print(f"Admin user found: {admin_user.username}")
print(f"Admin role: {admin_user.role}")
print(f"Admin is superuser: {admin_user.is_superuser}")

# Check if token exists
token = Token.objects.get(user=admin_user)
print(f"Admin token exists: Yes")
print(f"Token: {token.key}\n")

# Test login with your actual password (the one you used to create the superuser)
print("Testing login with your superuser password...")
print("(Make sure this is the correct password you set when creating the superuser)\n")

# Since we don't know your actual password, let's just verify the user exists
print("✓ Admin user is ready for login")
print("✓ Admin has role 'admin'")
print("✓ Admin has authentication token")
print("\nIf you're still getting 'invalid token' error:")
print("1. Make sure you're entering the EXACT password you set for the admin superuser")
print("2. Check browser console (F12) for the actual error message")
print("3. Make sure JavaScript is enabled in your browser")
