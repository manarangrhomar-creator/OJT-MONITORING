#!/usr/bin/env python
import os
import django
import secrets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import User

admin_password = os.environ.get('ADMIN_PASSWORD')
if not admin_password:
    admin_password = secrets.token_urlsafe(12)
    print(f"WARNING: No ADMIN_PASSWORD env var set. Generated random password.")

# Delete old admin user to start fresh
User.objects.filter(username='admin').delete()

# Create new admin with known password
admin = User.objects.create_user(
    username='admin',
    email='admin@isu.edu.ph',
    password=admin_password,
    first_name='Admin',
    last_name='User',
    is_superuser=True,
    is_staff=True,
    role='admin'
)

print("\n✅ ADMIN ACCOUNT CREATED")
print("="*50)
print(f"Username: admin")
print(f"Password: {admin_password}")
print(f"Email: admin@isu.edu.ph")
print(f"Role: admin")
print(f"Superuser: {admin.is_superuser}")
print("="*50)
print("\nTry logging in with these credentials now!")
