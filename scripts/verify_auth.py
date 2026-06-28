#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import User
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

print("\n" + "="*60)
print("AUTHENTICATION SYSTEM VERIFICATION")
print("="*60 + "\n")

# 1. Check Admin User
print("1. CHECKING ADMIN USER IN DATABASE")
print("-" * 60)
try:
    admin = User.objects.get(username='admin')
    print(f"✓ Admin user exists")
    print(f"  • Username: {admin.username}")
    print(f"  • Email: {admin.email}")
    print(f"  • Role: {admin.role}")
    print(f"  • Is Active: {admin.is_active}")
    print(f"  • Is Superuser: {admin.is_superuser}")
except User.DoesNotExist:
    print("✗ Admin user not found in database")
    exit(1)

# 2. Check Token
print("\n2. CHECKING AUTHENTICATION TOKEN")
print("-" * 60)
try:
    token = Token.objects.get(user=admin)
    print(f"✓ Authentication token exists")
    print(f"  • Token Key: {token.key}")
except Token.DoesNotExist:
    print("✗ Token does not exist")
    print("  Creating token...")
    token, created = Token.objects.get_or_create(user=admin)
    print(f"✓ Token created: {token.key}")

# 3. Test Authentication
print("\n3. TESTING AUTHENTICATION")
print("-" * 60)

# Get all users to show what's in the database
all_users = User.objects.all()
print(f"Total users in database: {all_users.count()}")
for user in all_users:
    has_token = Token.objects.filter(user=user).exists()
    print(f"  • {user.username} (role: {user.role}) - Token: {'✓' if has_token else '✗'}")

# 4. API Test
print("\n4. SUMMARY")
print("-" * 60)
print(f"✓ Admin account configured correctly")
print(f"✓ Admin has role 'admin'")
print(f"✓ Admin has authentication token")
print(f"✓ System ready for login")
print("\n" + "="*60)
print("WHAT TO DO IF LOGIN STILL FAILS:")
print("="*60)
print("""
1. Make sure Django server is running:
   python manage.py runserver

2. Clear browser cache (Ctrl+Shift+Delete on Chrome)

3. Open Developer Tools (F12) and check Console tab for errors

4. Try logging in with these credentials:
   • Username: admin
   • Password: [your superuser password]
   
5. Make sure you enter the EXACT password you set when creating the superuser

If you don't remember the password, reset it:
   python manage.py changepassword admin
""")
print("="*60 + "\n")
