# OJT Monitoring System - Django

A comprehensive Django-based OJT (On-the-Job Training) Monitoring System for Isabela State University with role-based authentication for Admins, Coordinators, and Students.

## Features

- **Role-Based Authentication**: Admin, Coordinator, and Student roles with specific dashboards
- **OJT Program Management**: Create and manage OJT programs
- **Application Management**: Student applications with approval/rejection workflow
- **Attendance Tracking**: Track student attendance with clock in/out functionality
- **Facial Recognition**: Integration for facial recognition-based attendance
- **Admin Dashboard**: System administration and user management
- **RESTful API**: Complete API documentation with Swagger UI
- **Database**: PostgreSQL for robust data management
- **Security**: CORS, CSRF protection, password validation

## Project Structure

```
ojt_monitoring/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── ojt_monitoring/           # Project settings
│   ├── settings.py          # Django configuration (PostgreSQL)
│   ├── urls.py              # Main URL routing
│   ├── wsgi.py
│   ├── asgi.py
│   └── __init__.py
├── apps/
│   ├── core/                # Base models and user management
│   ├── authentication/       # Login, registration, password reset
│   ├── admin_panel/         # Admin dashboard and system logs
│   ├── coordinator/         # OJT programs, applications, attendance
│   └── student/             # Student profiles, facial recognition
├── static/                  # CSS, JavaScript, images
├── media/                   # User uploads (profile pictures, documents)
├── templates/               # HTML templates (to be created in Phase 4)
└── logs/                    # Application logs
```

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- pip and virtualenv

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd ojt_monitoring
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure PostgreSQL Database
```bash
# Create PostgreSQL database
createdb ojt_monitoring_db

# Create database user
createuser ojt_admin -P  # Enter password when prompted
```

### Step 5: Create Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
# Update DATABASE credentials, SECRET_KEY, etc.
```

**Key Environment Variables:**
```
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ojt_monitoring_db
DB_USER=ojt_admin
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Step 6: Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Create Superuser
```bash
python manage.py createsuperuser
```

### Step 8: Run Development Server
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/me/` - Get current user
- `POST /api/auth/change_password/` - Change password

### Admin Panel
- `GET /api/admin/dashboard/dashboard_stats/` - Dashboard statistics
- `GET /api/admin/dashboard/system_logs/` - System logs
- `GET/POST /api/admin/users/` - User management

### Coordinator
- `GET/POST /api/coordinator/programs/` - OJT programs
- `GET/POST /api/coordinator/applications/` - Manage applications
- `POST /api/coordinator/applications/{id}/approve/` - Approve application
- `POST /api/coordinator/applications/{id}/reject/` - Reject application
- `GET/POST /api/coordinator/attendance/` - Attendance tracking
- `POST /api/coordinator/attendance/clock_in/` - Clock in
- `POST /api/coordinator/attendance/{id}/clock_out/` - Clock out

### Student
- `GET /api/student/dashboard/dashboard/` - Student dashboard
- `GET /api/student/dashboard/my_applications/` - My applications
- `GET /api/student/dashboard/my_attendance/` - My attendance
- `GET/POST /api/student/profile/` - Profile management
- `GET /api/student/profile/my_profile/` - My profile
- `PUT/PATCH /api/student/profile/update_profile/` - Update profile
- `GET/POST /api/student/facial/` - Facial recognition
- `POST /api/student/facial/enroll_face/` - Enroll face
- `POST /api/student/facial/verify_face/` - Verify face

## Admin Interface
Access the Django admin interface at `http://localhost:8000/admin/`

Manage:
- Users and roles
- OJT Programs
- Applications
- Attendance records
- System logs

## API Documentation
- Swagger UI: `http://localhost:8000/api/docs/`
- Schema: `http://localhost:8000/api/schema/`

## Static Files and Media
- Static files (CSS, JS, images): `static/`
- User uploads: `media/`

Collect static files for production:
```bash
python manage.py collectstatic --noinput
```

## Testing

Run tests with:
```bash
python manage.py test
```

## Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn ojt_monitoring.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker
```bash
docker build -t ojt-monitoring .
docker run -p 8000:8000 ojt-monitoring
```

### Production Checklist
1. Set `DEBUG=False`
2. Generate a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Set up HTTPS/SSL
5. Configure email settings
6. Set up database backups
7. Configure static files serving (WhiteNoise or separate web server)
8. Set up logging and monitoring

## Database Models

### Core
- **User**: Extended Django user with role-based access
- **BaseModel**: Abstract base model with timestamps

### Authentication
- **LoginAttempt**: Track login attempts for security

### Admin Panel
- **SystemLog**: Log system activities
- **SystemSettings**: Store system-wide settings

### Coordinator
- **OJTProgram**: OJT program information
- **OJTApplication**: Student applications
- **Attendance**: Attendance tracking records

### Student
- **StudentProfile**: Extended student profile
- **FacialRecognition**: Facial recognition data

## Next Phases

### Phase 2: Database & Models ✓
Database schema and models created with relationships

### Phase 3: Authentication & Authorization
- JWT token authentication
- Advanced permission system
- Facial recognition integration

### Phase 4: Frontend Templates
- Convert HTML templates to Django templates
- Implement Tailwind CSS styling
- Interactive forms and dashboards

### Phase 5: Views & URLs
- Complete REST API endpoints
- OJT program management
- Attendance & approval workflow

### Phase 6: Frontend Integration
- Tailwind CSS setup
- JavaScript integration
- Real-time updates

### Phase 7: Testing & Deployment
- Unit and integration tests
- Production deployment configuration

## Contributing

1. Create a feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit changes (`git commit -m 'Add AmazingFeature'`)
3. Push to the branch (`git push origin feature/AmazingFeature`)
4. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues and support, please contact the development team or create an issue in the repository.

## Acknowledgments

- Isabela State University
- Django Framework
- Django REST Framework
- PostgreSQL

---

**Last Updated**: May 26, 2026
