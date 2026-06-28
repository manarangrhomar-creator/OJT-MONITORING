#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import User
from rest_framework.authtoken.models import Token

print("\n" + "="*70)
print("SUPERUSER AUTO-ROLE ASSIGNMENT TEST")
print("="*70 + "\n")

# Test 1: Check existing admin
print("TEST 1: Checking existing admin superuser")
print("-" * 70)
admin = User.objects.get(username='admin')
print(f"Admin user: {admin.username}")
print(f"Is superuser: {admin.is_superuser}")
print(f"Role: {admin.role}")
print(f"✓ Signal working: {admin.is_superuser and admin.role == 'admin'}\n")

# Test 2: Create a test superuser via create_superuser
print("TEST 2: Creating new superuser via create_superuser()")
print("-" * 70)
try:
    # Delete if exists
    User.objects.filter(username='test_superuser').delete()
    
    test_super = User.objects.create_superuser(
        username='test_superuser',
        email='test_super@test.com',
        password='TestSuper1234'
    )
    print(f"✓ Created superuser: {test_super.username}")
    print(f"  Is superuser: {test_super.is_superuser}")
    print(f"  Role: {test_super.role}")
    print(f"  ✓ Signal worked correctly: {test_super.role == 'admin'}\n")
    
    # Create token for this user
    token, created = Token.objects.get_or_create(user=test_super)
    print(f"✓ Token created: {token.key[:20]}...\n")
    
    # Clean up
    test_super.delete()
    print(f"✓ Test superuser deleted\n")
    
except Exception as e:
    print(f"✗ Error: {e}\n")

print("="*70)
print("HOW IT WORKS")
print("="*70)
print("""
When you create a superuser in Django admin (or via create_superuser):

1. The User is saved to the database with is_superuser=True
2. Django sends a post_save signal
3. Our signal handler catches it
4. If is_superuser=True and role != 'admin':
   - Automatically sets role to 'admin'
   - Saves the user
5. User can now login with the web authentication system!

NEW SUPERUSERS WILL AUTOMATICALLY GET:
✓ is_superuser = True
✓ role = 'admin'
✓ Can access Django admin (/admin/)
✓ Can login to web admin panel (/auth/admin/login/)
✓ Can access admin dashboard (/dashboard/admin/)
""")
print("="*70 + "\n")
