import os, django, json, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ojt_monitoring.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import Client
from apps.core.models import User, Course
from rest_framework.authtoken.models import Token

c = Client(enforce_csrf_checks=False)

# Clean up test users
User.objects.filter(username='tcoord').delete()
User.objects.filter(username='tcoord2').delete()
User.objects.filter(username='stu1').delete()
Course.objects.filter(name='BSIT').delete()

course = Course.objects.create(name='BSIT')

# Create coordinator
u = User.objects.create_user(
    username='tcoord', email='c@t.com', password=os.environ.get('TEST_PASSWORD', 'changeme'),
    role='coordinator', course=course, approval_status='approved',
    first_name='Test', last_name='Coord'
)
t, _ = Token.objects.get_or_create(user=u)

print('=== Test 1: Create program ===')
r = c.post('/api/coordinator/programs/', json.dumps({
    'name': 'BSIT OJT 2026',
    'description': 'Test program',
    'max_students': 50
}), content_type='application/json', HTTP_AUTHORIZATION=f'Token {t.key}')
print(f'  Status: {r.status_code}')
if r.status_code != 201:
    print(f'  ERROR: {r.content.decode()}')
    sys.exit(1)
pid = r.json().get('id')
print(f'  Created ID: {pid}  PASS')

print()
print('=== Test 2: List coordinator programs (expect flat array) ===')
r = c.get('/api/coordinator/programs/', HTTP_AUTHORIZATION=f'Token {t.key}')
d = r.json()
print(f'  Type: {type(d).__name__}')
assert isinstance(d, list), f'Expected list, got {type(d).__name__}'
assert len(d) == 1, f'Expected 1, got {len(d)}'
assert d[0]['name'] == 'BSIT OJT 2026'
assert d[0]['coordinator_name'] == 'Test Coord'
print('  PASS')

print()
print('=== Test 3: New coordinator (no programs) ===')
u2 = User.objects.create_user(
    username='tcoord2', email='c2@t.com', password=os.environ.get('TEST_PASSWORD', 'changeme'),
    role='coordinator', approval_status='approved',
    first_name='New', last_name='Coord'
)
t2, _ = Token.objects.get_or_create(user=u2)
r = c.get('/api/coordinator/programs/', HTTP_AUTHORIZATION=f'Token {t2.key}')
d = r.json()
assert isinstance(d, list), f'Expected list, got {type(d).__name__}'
assert len(d) == 0, f'Expected 0, got {len(d)}'
print('  PASS (0 programs - overlay will show)')

print()
print('=== Test 4: Unauthenticated blocked ===')
r = c.post('/api/coordinator/programs/', json.dumps({'name': 'X'}),
           content_type='application/json')
assert r.status_code == 401, f'Expected 401, got {r.status_code}'
print('  PASS')

print()
print('=== Test 5: Student blocked ===')
stu = User.objects.create_user(
    username='stu1', email='s@t.com', password=os.environ.get('TEST_PASSWORD', 'changeme'),
    role='student', approval_status='approved'
)
t3, _ = Token.objects.get_or_create(user=stu)
r = c.post('/api/coordinator/programs/', json.dumps({'name': 'X'}),
           content_type='application/json', HTTP_AUTHORIZATION=f'Token {t3.key}')
assert r.status_code == 403, f'Expected 403, got {r.status_code}'
print('  PASS')

print()
print('=== ALL 5 TESTS PASSED ===')
