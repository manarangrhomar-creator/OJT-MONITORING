#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import User

# Delete old admin user to start fresh
User.objects.filter(username='admin').delete()

# Create new admin with known password
admin = User.objects.create_user(
    username='admin',
    email='admin@isu.edu.ph',
    password='Admin12345',
    first_name='Admin',
    last_name='User',
    is_superuser=True,
    is_staff=True,
    role='admin'
)

print("\n✅ ADMIN ACCOUNT CREATED")
print("="*50)
print(f"Username: admin")
print(f"Password: Admin12345")
print(f"Email: admin@isu.edu.ph")
print(f"Role: admin")
print(f"Superuser: {admin.is_superuser}")
print("="*50)
print("\nTry logging in with these credentials now!")
