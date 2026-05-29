#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import User
from rest_framework.authtoken.models import Token

print("\n" + "="*70)
print("✅ AUTOMATIC SUPERUSER → ADMIN ROLE SETUP COMPLETE")
print("="*70 + "\n")

# Show existing users
print("CURRENT SYSTEM USERS")
print("-" * 70)
for user in User.objects.all():
    is_super = "✓" if user.is_superuser else " "
    has_token = "✓" if Token.objects.filter(user=user).exists() else "✗"
    print(f"[{is_super}] {user.username:20} | Role: {user.role:15} | Token: {has_token}")

print("\n" + "="*70)
print("HOW TO CREATE A NEW ADMIN ACCOUNT")
print("="*70)
print("""
METHOD 1: Using Django Command Line
-----------------------------------
$ python manage.py createsuperuser

This will prompt for:
  - Username: [your username]
  - Email: [your email]
  - Password: [your password]
  - Password (again): [confirm password]

✓ Role will be AUTOMATICALLY set to 'admin'
✓ Auth token will be AUTOMATICALLY created
✓ User can login immediately at /auth/admin/login/

METHOD 2: Using Django Admin Interface
--------------------------------------
1. Go to http://localhost:8000/admin/
2. Login as existing admin
3. Click "Users"
4. Click "Add User"
5. Fill in username and password
6. Check the "Superuser status" checkbox ✓
7. Click "Save"

✓ Role will be AUTOMATICALLY set to 'admin'
✓ Auth token will be AUTOMATICALLY created
✓ User can login immediately at /auth/admin/login/

METHOD 3: Using Django Shell
-----------------------------
$ python manage.py shell

>>> from apps.core.models import User
>>> User.objects.create_superuser(
...     username='newadmin',
...     email='admin@example.com',
...     password='SecurePassword123'
... )

✓ Role will be AUTOMATICALLY set to 'admin'
✓ Auth token will be AUTOMATICALLY created
✓ User can login immediately at /auth/admin/login/
""")

print("="*70)
print("WHAT HAPPENS AUTOMATICALLY")
print("="*70)
print("""
When you create a superuser:

1. Django saves the user with is_superuser=True
2. A signal handler is triggered
3. Signal handler checks: if is_superuser and role != 'admin'
4. If true, automatically sets role='admin'
5. User is saved again with admin role
6. Token is automatically generated if missing
7. User is ready to login!

IN DJANGO ADMIN:
- Role field becomes READ-ONLY for superusers
- This prevents accidentally changing their role
- Makes it clear the role is auto-assigned

IN WEB LOGIN:
- User can login at /auth/admin/login/
- Credentials are validated against database ✓
- User is redirected to /dashboard/admin/
- Role-based access control is enforced ✓
""")

print("="*70)
print("TESTING YOUR NEW ADMIN ACCOUNT")
print("="*70)
print("""
1. Start Django server:
   $ python manage.py runserver

2. Create a new superuser:
   $ python manage.py createsuperuser
   [Enter your details]

3. Login to web admin:
   - Go to http://localhost:8000/auth/admin/login/
   - Enter your username and password
   - You should be redirected to admin dashboard ✓

4. Verify in Django admin:
   - Go to http://localhost:8000/admin/
   - Click Users
   - Find your new superuser
   - Role should show as 'admin' (and be read-only)
""")

print("="*70)
print("EXISTING SUPERUSER USERS")
print("="*70)
admins = User.objects.filter(is_superuser=True)
for admin in admins:
    has_token = Token.objects.filter(user=admin).exists()
    print(f"✓ {admin.username} - Role: {admin.role} - Token: {'✓' if has_token else '✗'}")

if not admins:
    print("No superusers found. Create one with:")
    print("  $ python manage.py createsuperuser")
    
print("\n" + "="*70 + "\n")
