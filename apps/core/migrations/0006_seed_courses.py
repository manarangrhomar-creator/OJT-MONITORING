from django.db import migrations


COURSES = [
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


def seed_courses(apps, schema_editor):
    Course = apps.get_model('core', 'Course')
    for name in COURSES:
        Course.objects.get_or_create(name=name)


def delete_courses(apps, schema_editor):
    Course = apps.get_model('core', 'Course')
    Course.objects.filter(name__in=COURSES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_course_alter_user_course'),
    ]

    operations = [
        migrations.RunPython(seed_courses, delete_courses),
    ]
