<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-4.2-green?logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/DRF-3.14-red?logo=django&logoColor=white" alt="DRF">
  <img src="https://img.shields.io/badge/PostgreSQL-12%2B-blue?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/Status-In%20Development-orange" alt="Status">
</p>

<h1 align="center">OJT Monitoring System</h1>
<p align="center">
  <em>A comprehensive Django-based On-the-Job Training Monitoring System for Isabela State University</em>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Workflows](#workflows)
  - [Student Workflow](#-student-workflow)
  - [Coordinator Workflow](#-coordinator-workflow)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [Implementation Status](#implementation-status)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The **OJT Monitoring System** streamlines the entire On-the-Job Training lifecycle at Isabela State University, from student registration and site assignment to daily attendance tracking, facial recognition verification, and performance evaluation. The system supports three roles: **Admin**, **Coordinator**, and **Student**, each with dedicated dashboards and workflows.

> PS. Run `setup.bat` to install all requirements automatically.

---

## Features

| Feature | Description |
|---------|-------------|
| :busts_in_silhouette: **Role-Based Auth** | Admin, Coordinator, and Student roles with gated dashboards |
| :school: **OJT Program Management** | Create, manage, and monitor training programs |
| :page_facing_up: **Application Workflow** | Student applications with approval/rejection by coordinators |
| :clock3: **Attendance Tracking** | Clock in/out with facial recognition verification |
| :camera: **Facial Recognition** | LBPH-based face enrollment and verification via webcam |
| :bar_chart: **Admin Dashboard** | User management, system logs, and coordinator approvals |
| :globe_with_meridians: **RESTful API** | Full API with Swagger/OpenAPI documentation |
| :lock: **Security** | Token authentication, login attempt tracking, role-based permissions |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.8+, Django 4.2, Django REST Framework 3.14 |
| **Database** | PostgreSQL 12+ |
| **Face Recognition** | OpenCV (LBPH algorithm) |
| **Frontend** | Django Templates, Tailwind CSS (CDN), Vanilla JS |
| **Authentication** | DRF Token Authentication + Django Sessions |
| **API Docs** | drf-spectacular (Swagger UI) |
| **Container** | Docker, docker-compose |

---

## System Architecture

```
ojt_monitoring/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile / docker-compose.yml
├── ojt_monitoring/           # Project configuration
│   ├── settings.py           # Django configuration (PostgreSQL)
│   ├── urls.py               # Main URL routing
│   ├── wsgi.py / asgi.py
│   └── middleware.py         # CSRF exemption middleware
├── apps/
│   ├── core/                 # Base models (User), dashboard routing, utilities
│   ├── authentication/       # Login, registration, login attempt tracking
│   ├── admin_panel/          # Admin dashboard, user CRUD, system logs
│   ├── coordinator/          # OJT programs, applications, attendance, reports
│   └── student/              # Student profiles, facial recognition, dashboard
├── static/                   # CSS, JavaScript, images
├── media/                    # User uploads (profile pictures, documents)
├── templates/                # Django HTML templates (Tailwind CSS)
└── logs/                     # Application logs
```

---

## Workflows

### :bust_in_silhouette: Student Workflow

```
Registration → Application → Coordinator Approval → Biometric Enrollment
                                                         ↓
                                              Site Assignment by Coordinator
                                                         ↓
┌────────────────────────────────────────────────────────────────────┐
│                    Daily Attendance Phase                          │
│                                                                   │
│  Time-In (Webcam Facial Recognition)                              │
│       ↓ (fail → retry)                                            │
│  Submit Daily Narrative Report                                    │
│       ↓                                                           │
│  Time-Out (Webcam)                                                │
└────────────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────────────┐
│  Post-Attendance Logic                                            │
│                                                                   │
│  Was manual time-out captured?                                    │
│  ├── YES → Record finalized                                       │
│  └── NO  → Automated Timeout triggered → Flagged for Review      │
└────────────────────────────────────────────────────────────────────┘
         ↓
  View Progress & Time-Tracking Records
```

### :busts_in_silhouette: Coordinator Workflow

```
Login → Dashboard
         ↓
├── Assign Students to Sites
├── Monitor Live/Recorded Attendance
├── Review & Evaluate Narrative Reports
├── Review Flagged/Automated Timeouts
└── Review Time-Tracking Records
```

---

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip and virtualenv

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd ojt_monitoring

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure PostgreSQL database
createdb ojt_monitoring_db
createuser ojt_admin -P

# 5. Configure environment variables
cp .env.example .env
# Edit .env with your database credentials

# 6. Apply migrations
python manage.py makemigrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver
```

The application will be available at `http://localhost:8000`

### Key Environment Variables

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

---

## API Endpoints

### :lock: Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | User login |
| POST | `/api/auth/logout/` | User logout |
| GET | `/api/auth/me/` | Get current user |
| POST | `/api/auth/change_password/` | Change password |

### :wrench: Admin Panel

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/dashboard/dashboard_stats/` | Dashboard statistics |
| GET | `/api/admin/dashboard/system_logs/` | System activity logs |
| GET/POST | `/api/admin/users/` | User management |

### :busts_in_silhouette: Coordinator

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/coordinator/programs/` | OJT program CRUD |
| GET/POST | `/api/coordinator/applications/` | Manage applications |
| POST | `/api/coordinator/applications/{id}/approve/` | Approve application |
| POST | `/api/coordinator/applications/{id}/reject/` | Reject application |
| POST | `/api/coordinator/attendance/clock_in/` | Clock in |
| POST | `/api/coordinator/attendance/{id}/clock_out/` | Clock out |
| GET | `/api/coordinator/dashboard/my-students/` | My students |

### :student: Student

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/student/dashboard/dashboard/` | Student dashboard |
| GET | `/api/student/dashboard/my_applications/` | My applications |
| GET | `/api/student/dashboard/my_attendance/` | My attendance records |
| GET | `/api/student/profile/my_profile/` | My profile |
| PUT | `/api/student/profile/update_profile/` | Update profile |
| POST | `/api/student/facial/enroll_face/` | Enroll facial biometrics |
| POST | `/api/student/facial/verify_face/` | Verify face for attendance |

> **API Documentation:** Swagger UI at `http://localhost:8000/api/docs/` | OpenAPI Schema at `http://localhost:8000/api/schema/`

---

## Database Models

### :bust_in_silhouette: Core

| Model | Description |
|-------|-------------|
| **User** | Extended Django `AbstractUser` with role (admin/coordinator/student), approval status, phone, course, profile picture, faculty ID |
| **BaseModel** | Abstract base with auto `created_at` / `updated_at` timestamps |

### :key: Authentication

| Model | Description |
|-------|-------------|
| **LoginAttempt** | Tracks login IP, success/failure, user agent for security auditing |

### :wrench: Admin Panel

| Model | Description |
|-------|-------------|
| **SystemLog** | Records system activities (user created/deleted, approvals, reports) |
| **SystemSettings** | Key-value store for system-wide configuration |

### :busts_in_silhouette: Coordinator

| Model | Description |
|-------|-------------|
| **OJTProgram** | OJT program details (name, description, dates, location, max students, coordinator) |
| **OJTApplication** | Student applications linking to programs (status: pending/approved/rejected/completed) |
| **Attendance** | Daily attendance records (date, time-in, time-out, facial recognition flag, notes) |

### :student: Student

| Model | Description |
|-------|-------------|
| **StudentProfile** | Extended profile (student ID, department, course, year level, GPA) |
| **FacialRecognition** | LBPH facial encodings with verification status and date |

---

## Implementation Status

### :green_circle: Fully Implemented

| # | Feature | Notes |
|---|---------|-------|
| 1 | :busts_in_silhouette: Role-based authentication | Admin, Coordinator, Student with DRF tokens |
| 2 | :door: User registration & login | Email/ID login, token session management |
| 3 | :key: Password change | Requires old password |
| 4 | :bust_in_silhouette: Admin user management | CRUD for students & coordinators |
| 5 | :white_check_mark: Admin coordinator approval | Pending/approved/rejected workflow |
| 6 | :books: OJT Program CRUD | Create, update, manage programs |
| 7 | :page_facing_up: OJT Application workflow | Submit & approve/reject applications |
| 8 | :camera: Facial recognition enrollment | Webcam capture, LBPH encoding storage |
| 9 | :camera: Facial recognition verification | Webcam-based identity verification |
| 10 | :clock3: Attendance time-in/time-out API | Coordinator-side clock in/out |
| 11 | :eyes: **Coordinator Attendance Monitoring** | Full dashboard with filters, student accounts, attendance records |
| 12 | :bar_chart: System activity logging | Login attempts, admin actions |
| 13 | :globe_with_meridians: Swagger API docs | Auto-generated OpenAPI documentation |
| 14 | :whale: Docker support | Dockerfile + docker-compose.yml |
| 15 | :bar_chart: **Student Dashboard** | Live API data, dynamic hours display, attendance history table |
| 16 | :chart_with_upwards_trend: **Progress Tracking** | Rendered/remaining hours calculated from real attendance data |
| 17 | :envelope: **Forgot Password** | 3-step OTP flow (email → verify → reset) with full backend API |
| 18 | :link: **Site Assignments** | Coordinators assign students to sites with supervisor info |
| 19 | :memo: **Student Narrative Reports** | Daily accomplishments with topic, content, and up to 4 photo uploads |
| 20 | :file_cabinet: **Student Narrative Archives** | View, edit, manage submitted narratives with photo gallery |
| 21 | :round_pushpin: **Geolocation Verification** | GPS lat/lon + IP address captured on clock-in |
| 22 | :alarm_clock: **Automated Timeout** | Celery task auto-clockouts stale attendances >10h, creates FlagRecord |
| 23 | :triangular_flag_on_post: **Flagged Records System** | FlagRecord model + coordinator resolve flow |
| 24 | :bell: **Notification System** | In-app notifications + email via Celery task + WebSocket broadcast |
| 25 | :arrows_counterclockwise: **Celery/Redis Task Queue** | send_email_task + auto_clockout_stale_attendances tasks defined |
| 26 | :stopwatch: **Rate Limiting** | Custom throttling classes on auth endpoints |
| 27 | :e-mail: **Email Verification** | Token-based email verification on student registration |
| 28 | :chart_with_upwards_trend: **Reporting & Analytics** | CSV attendance export + coordinator dashboard stats endpoint |

### :yellow_circle: Partially Implemented

| # | Feature | What's Missing |
|---|---------|----------------|

### :red_circle: Not Implemented

| # | Feature | Description |
|---|---------|-------------|
| 1 | :camera: **Student Webcam Time-Out** | No student-facing clock-out flow via webcam (student clock-out exists but not via webcam) |
| 2 | :test_tube: **Test Coverage** | Test files are auto-generated placeholders only |

---

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

---

## Contributing

1. Create a feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit changes (`git commit -m 'Add AmazingFeature'`)
3. Push to the branch (`git push origin feature/AmazingFeature`)
4. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- **Isabela State University** — Project sponsor and stakeholder
- **Django Framework** & **Django REST Framework** — Backend framework
- **OpenCV** — Computer vision library for facial recognition

---

<p align="center">
  <sub>Built with :heart: for Isabela State University</sub>
  <br>
  <sub>Last Updated: June 2026</sub>
</p>
