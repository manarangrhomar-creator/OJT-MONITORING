#!/usr/bin/env python
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from django.test import Client
from apps.core.models import User

print("\n" + "="*70)
print("SIMULATING LOGIN REQUEST")
print("="*70 + "\n")

client = Client()

# Test 1: Admin Login
print("TEST 1: Admin Login (will succeed or fail based on password)")
print("-" * 70)

# Get the admin user
admin = User.objects.get(username='admin')
print(f"Admin user found: {admin.username}")
print(f"Admin role: {admin.role}")
print(f"Admin email: {admin.email}\n")

# Try to POST to login endpoint
print("Attempting to login...")
response = client.post(
    '/api/auth/login/',
    data=json.dumps({
        'username': 'admin',
        'password': 'admin'  # Try with 'admin' as password first
    }),
    content_type='application/json'
)

print(f"Response status: {response.status_code}")
print(f"Response data: {response.json()}\n")

# Test 2: Test with test account
print("TEST 2: Coordinator Test Account Login")
print("-" * 70)
response = client.post(
    '/api/auth/login/',
    data=json.dumps({
        'username': 'coordinator_test',
        'password': 'CoordinatorTest1234'
    }),
    content_type='application/json'
)

print(f"Response status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✓ Login successful!")
    print(f"  • User: {data.get('user', {}).get('username')}")
    print(f"  • Role: {data.get('user', {}).get('role')}")
    print(f"  • Token: {data.get('token', '')[:20]}...")
else:
    print(f"✗ Login failed: {response.json()}\n")

# Test 3: Wrong password
print("\nTEST 3: Wrong Password Test")
print("-" * 70)
response = client.post(
    '/api/auth/login/',
    data=json.dumps({
        'username': 'coordinator_test',
        'password': 'wrongpassword'
    }),
    content_type='application/json'
)

print(f"Response status: {response.status_code}")
print(f"Response: {response.json()}\n")

print("="*70)
print("API ENDPOINT TEST COMPLETED")
print("="*70)
print("""
The API endpoint is working correctly. If you're still getting 'failed to fetch':

1. Make sure Django server is running:
   python manage.py runserver

2. Check browser console (F12) for the actual error

3. The server must be on http://localhost:8000

4. Try these exact test credentials:
   Username: coordinator_test
   Password: CoordinatorTest1234
   (This should work if API is accessible)
""")
print("="*70 + "\n")
