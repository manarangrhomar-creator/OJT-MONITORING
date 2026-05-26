# QUICK START GUIDE

## Phase 1 - Complete! ✓

Your Django OJT Monitoring System is ready to set up. Follow these steps to get started.

## Step 1: Install PostgreSQL

### On Windows
- Download from: https://www.postgresql.org/download/windows/
- Run installer and remember the password you set for `postgres` user
- PostgreSQL will run on port 5432

### On macOS
```bash
brew install postgresql@15
brew services start postgresql@15
```

### On Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo service postgresql start
```

## Step 2: Create Database and User

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql prompt, run:
CREATE DATABASE ojt_monitoring_db;
CREATE USER ojt_admin WITH PASSWORD 'your-secure-password';
ALTER ROLE ojt_admin SET client_encoding TO 'utf8';
ALTER ROLE ojt_admin SET default_transaction_isolation TO 'read committed';
ALTER ROLE ojt_admin SET default_transaction_deferrable TO on;
ALTER ROLE ojt_admin SET timezone TO 'Asia/Manila';
GRANT ALL PRIVILEGES ON DATABASE ojt_monitoring_db TO ojt_admin;
\q
```

## Step 3: Setup Django Project

### On Windows
```bash
cd ojt_monitoring
setup.bat
```

### On macOS/Linux
```bash
cd ojt_monitoring
chmod +x setup.sh
./setup.sh
```

### Manual Setup (if scripts don't work)
```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

## Step 4: Run Development Server

```bash
python manage.py runserver
```

The application will be available at: **http://localhost:8000**

## Access Points

- **Admin Interface**: http://localhost:8000/admin/
  - Login with your superuser credentials
  - Manage users, programs, applications, attendance
  
- **API Documentation**: http://localhost:8000/api/docs/
  - Interactive Swagger UI
  - Test all API endpoints
  
- **API Schema**: http://localhost:8000/api/schema/

## API Endpoints

### Authentication (No login required)
```
POST   /api/auth/register/        - Register new user
POST   /api/auth/login/           - User login
```

### After Login
```
POST   /api/auth/logout/          - User logout
GET    /api/auth/me/              - Get current user
POST   /api/auth/change_password/ - Change password
```

### Admin Only (role=admin)
```
GET    /api/admin/dashboard/dashboard_stats/
GET    /api/admin/dashboard/system_logs/
GET    /api/admin/users/
```

### Coordinator Only (role=coordinator)
```
GET/POST   /api/coordinator/programs/
GET/POST   /api/coordinator/applications/
GET/POST   /api/coordinator/attendance/
```

### Student Only (role=student)
```
GET    /api/student/dashboard/dashboard/
GET    /api/student/dashboard/my_applications/
GET/POST   /api/student/profile/
```

## Testing the System

### Create Test Users

In Django shell:
```bash
python manage.py shell
```

```python
from apps.core.models import User

# Create admin
admin = User.objects.create_user(
    username='admin1',
    email='admin@example.com',
    password='admin123',
    first_name='Admin',
    last_name='User',
    role='admin'
)

# Create coordinator
coordinator = User.objects.create_user(
    username='coordinator1',
    email='coordinator@example.com',
    password='coor123',
    first_name='John',
    last_name='Coordinator',
    role='coordinator'
)

# Create student
student = User.objects.create_user(
    username='student1',
    email='student@example.com',
    password='student123',
    first_name='Jane',
    last_name='Student',
    role='student'
)

exit()
```

### Test Login with curl
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"student123"}'
```

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to database server
```
**Solution**: 
- Ensure PostgreSQL is running
- Check credentials in .env match your setup
- Run: `psql -U ojt_admin -d ojt_monitoring_db` to test connection

### Port Already in Use
```
Error: Address already in use
```
**Solution**:
```bash
# Use different port
python manage.py runserver 8001
```

### Migration Error
```bash
# Reset migrations (if needed)
python manage.py migrate zero
python manage.py makemigrations
python manage.py migrate
```

## Using Docker (Optional)

```bash
# Build and run with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Stop containers
docker-compose down
```

## Project Structure

```
ojt_monitoring/
├── manage.py                  # Django management
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create from .env.example)
├── ojt_monitoring/            # Project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                  # Base models
│   ├── authentication/        # Auth endpoints
│   ├── admin_panel/          # Admin features
│   ├── coordinator/          # OJT management
│   └── student/              # Student features
├── templates/                 # HTML templates
├── static/                    # CSS, JS, images
├── media/                     # User uploads
└── README.md                  # Full documentation
```

## Next Steps

1. **Phase 2**: Database Models & Migrations
2. **Phase 3**: Facial Recognition Integration
3. **Phase 4**: HTML Templates to Django Templates
4. **Phase 5**: Complete API Implementation
5. **Phase 6**: Frontend JavaScript Integration
6. **Phase 7**: Testing & Production Deployment

## Support

- Check **README.md** for comprehensive documentation
- Check **DEVELOPMENT.md** for development guides
- Review Django documentation: https://docs.djangoproject.com/
- Check DRF documentation: https://www.django-rest-framework.org/

---

**Start the server now!**
```bash
python manage.py runserver
```

Then visit: **http://localhost:8000/admin/**
