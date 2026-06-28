# AGENTS.md — OJT Monitoring System

## Commands

| Action | Command |
|--------|---------|
| Dev server | `python manage.py runserver` |
| Test all | `python manage.py test` |
| Test one app | `python manage.py test apps.core` (or `authentication`, `admin_panel`, `coordinator`, `student`) |
| Shell | `python manage.py shell` |
| Make + apply migrations | `python manage.py makemigrations; python manage.py migrate` |
| Static files | `python manage.py collectstatic --noinput` |
| Stub user creation | `python manage.py createsuperuser` |
| Docker full stack | `docker-compose up` (starts db, redis, web, celery worker) |
| Celery (Windows) | `celery -A ojt_monitoring worker -l info --pool=solo` |

No linter, formatter, typechecker, pre-commit, or CI config exists. Tests are minimal placeholders.

## Architecture

- **Django 4.2 + DRF 3.14**, custom `User` model (`apps/core/models.py:9`, UUID PK, `role` in `admin|coordinator|student`)
- **DRF Token Auth** (`rest_framework.authtoken`), CSRF middleware disabled (`settings.py:71`)
- **ASGI** via Daphne/Channels — WebSocket consumers at `apps/core/consumers.py`
- **Celery** with Redis broker; `CELERY_TASK_ALWAYS_EAGER=True` by default so tasks run synchronously unless a Redis is running
- **SQLite** for dev (`settings.py:120-126`), PostgreSQL in Docker/production; `.env` PostgreSQL vars are NOT used by settings.py (sqlite3 is hardcoded)
- **drf-spectacular** at `/api/docs/` (Swagger), `/api/schema/` (OpenAPI)
- All endpoints use **DRF ViewSets + DefaultRouter**; check each app's `urls.py` for generated routes

## App structure

| App | Models | Routes prefix |
|-----|--------|--------------|
| `core` | `User`, `Course`, `Notification` | `/api/` (notifications WS) |
| `authentication` | `PasswordResetOTP`, `LoginAttempt` | `/api/auth/` |
| `admin_panel` | `SystemLog`, `SystemSettings` | `/api/admin/` |
| `coordinator` | `OJTProgram`, `OJTApplication`, `Attendance`, `Site`, `SiteAssignment` | `/api/coordinator/` |
| `student` | `StudentProfile`, `StudentNarrativeReport`, `FacialRecognition` | `/api/student/` |

## Key quirks

- Superusers auto-get `role='admin'` via `post_save` signal in `apps/core/models.py:52-60`
- Login accepts `identifier` field (username or email)
- Student registration creates `StudentProfile` but does NOT log user in — requires coordinator approval
- Forgot password uses 3-step OTP flow: send OTP → verify OTP → reset password
- Docker/web entrypoint runs `migrate` then `runserver`; no `makemigrations` step
- The `.env` file contains real Gmail credentials — do not commit or expose
- `ALLOWED_HOSTS` includes `*` — permissive in dev

## Frontend

- Django templates in `templates/`, Tailwind CSS via CDN, vanilla JS
- `static/js/auth.js` handles token storage, login/register/logout, role-based redirect
- WebSocket at `ws://host/ws/notifications/?token=...` and `ws://host/ws/dashboard/?token=...`
