# Development & Testing Guide for OJT Monitoring System

## Running Tests

### Run all tests
```bash
python manage.py test
```

### Run tests for specific app
```bash
python manage.py test apps.core
python manage.py test apps.authentication
python manage.py test apps.admin_panel
python manage.py test apps.coordinator
python manage.py test apps.student
```

### Run with verbose output
```bash
python manage.py test -v 2
```

## Database Management

### Create new migration
```bash
python manage.py makemigrations
```

### Apply migrations
```bash
python manage.py migrate
```

### Show migration status
```bash
python manage.py showmigrations
```

### Revert migration
```bash
python manage.py migrate app_name 0001
```

## Shell Commands

### Access Django shell
```bash
python manage.py shell
```

### Common shell operations
```python
# Create user
from apps.core.models import User
user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='password123',
    role='student'
)

# Create OJT Program
from apps.coordinator.models import OJTProgram
program = OJTProgram.objects.create(
    name='OJT Program 2024',
    start_date='2024-06-01',
    end_date='2024-08-31',
    coordinator=user
)
```

## Development Tips

### Enable Django Debug Toolbar (for development)
```bash
pip install django-debug-toolbar
```

Then add to `INSTALLED_APPS`:
```python
'debug_toolbar',
```

### Create fixture data
```bash
python manage.py dumpdata > fixtures/initial_data.json
python manage.py loaddata fixtures/initial_data.json
```

## API Testing

### Using curl
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "email": "student1@example.com",
    "password": "securepass123",
    "password2": "securepass123",
    "first_name": "John",
    "last_name": "Doe",
    "role": "student"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student1",
    "password": "securepass123"
  }'
```

### Using Postman
1. Import the API collection (to be created in Phase 4)
2. Set up environment variables for base URL and auth tokens
3. Test each endpoint with sample data

## Performance Optimization

### Database Query Optimization
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse foreign keys
- Use `.only()` or `.defer()` to limit fields

Example:
```python
# Good
applications = OJTApplication.objects.select_related('student', 'program').all()

# Avoid N+1 queries
for app in applications:
    print(app.student.name)
```

### Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def cached_view(request):
    pass
```

## Debugging

### Print statements in views
```python
import logging
logger = logging.getLogger(__name__)
logger.debug('Debug message')
logger.info('Info message')
logger.warning('Warning message')
logger.error('Error message')
```

### Django logging configuration is in settings.py

## Common Issues

### PostgreSQL Connection Error
- Ensure PostgreSQL is running
- Check DB credentials in .env
- Verify database exists

### Migration issues
```bash
# Reset migrations (USE WITH CAUTION)
python manage.py migrate app_name zero
python manage.py makemigrations
python manage.py migrate
```

### Static files not loading
```bash
python manage.py collectstatic --clear --noinput
```

## Production Deployment

### Pre-deployment checklist
- [ ] Set `DEBUG=False`
- [ ] Generate new `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up HTTPS/SSL
- [ ] Configure environment variables
- [ ] Run `collectstatic`
- [ ] Run database migrations
- [ ] Set up monitoring/logging
- [ ] Test all authentication flows
- [ ] Backup database

