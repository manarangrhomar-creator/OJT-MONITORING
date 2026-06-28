"""
Seed initial course data for the OJT Monitoring System.
Run with: python manage.py shell < seed_data.py
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
django.setup()

from apps.core.models import Course, User
from apps.coordinator.models import Site
from apps.student.models import StudentProfile

DEFAULT_COURSES = [
    "BS Information Technology (BSIT)",
    "BS Computer Science (BSCS)",
    "Bachelor of Entertainment and Multimedia Computing (BEMC)",
    "Bachelor of Elementary Education (BEED)",
    "Bachelor of Secondary Education (BSED)",
    "Bachelor of Physical Education (BPED)",
    "BS Business Administration",
    "BS Entrepreneurship",
    "BS Management Accounting",
    "BS Accounting Information System",
    "BS Hospitality Management",
    "BS Tourism Management",
    "BA Political Science",
    "BA English Language Studies",
    "BS Psychology",
    "BS Legal Management",
    "BS Agriculture",
    "Bachelor of Agricultural Technology",
    "BS Food Technology",
    "BS Criminology",
]

# Seed courses
for name in DEFAULT_COURSES:
    Course.objects.get_or_create(name=name)

print(f"[OK] Seeded {Course.objects.count()} courses")

# Link existing users' course references
for user in User.objects.all():
    if user.course and isinstance(user.course, str):
        try:
            course = Course.objects.get(name=user.course)
            user.course = course
            user.save(update_fields=['course'])
            print(f"  Linked user {user.username} -> {course.name}")
        except Course.DoesNotExist:
            print(f"  ! Course '{user.course}' not found for user {user.username}")

# Link existing student profiles' course references
for sp in StudentProfile.objects.all():
    if sp.course and isinstance(sp.course, str):
        try:
            course = Course.objects.get(name=sp.course)
            sp.course = course
            sp.save(update_fields=['course'])
            print(f"  Linked student {sp.user.username} -> {course.name}")
        except Course.DoesNotExist:
            print(f"  ! Course '{sp.course}' not found for student {sp.user.username}")

print("[OK] Seed complete")
