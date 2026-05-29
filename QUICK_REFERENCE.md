# 🎯 QUICK REFERENCE - OJT Monitoring Authentication

## Test Accounts (Ready to Use)

| Role | Username | Password | URL |
|------|----------|----------|-----|
| 👨‍💼 Admin | `admin_test` | `AdminTest1234` | /auth/admin/login/ |
| 👨‍🏫 Coordinator | `coordinator_test` | `CoordinatorTest1234` | /auth/coordinator/login/ |
| 👨‍🎓 Student | `student_test` | `StudentTest1234` | /auth/student/login/ |

## What Changed

### ✅ Databases Now Used
- ✅ User credentials validated against database
- ✅ Roles checked and enforced
- ✅ Login attempts tracked
- ✅ Tokens stored securely

### ✅ New Files
```
/static/js/auth.js                    - Authentication logic
/apps/core/dashboard_views.py         - Role protection
/setup_auth.py                        - Test setup script
```

### ✅ Updated Files
```
/apps/authentication/views.py         - API auth endpoints
/ojt_monitoring/settings.py           - Token auth enabled
/ojt_monitoring/urls.py               - Protected routes
/templates/*_login.html               - Forms connected to API
```

## API Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| `POST` | `/api/auth/login/` | Authenticate user |
| `POST` | `/api/auth/register/` | Create new account |
| `POST` | `/api/auth/logout/` | Logout user |
| `GET` | `/api/auth/me/` | Get current user |

## Protected Routes

| URL | Allowed Role | Protection |
|-----|--------------|-----------|
| `/dashboard/admin/` | admin | ✅ Enforced |
| `/dashboard/coordinator/` | coordinator | ✅ Enforced |
| `/dashboard/student/` | student | ✅ Enforced |

## Quick Test Steps

1. **Start Server**
   ```bash
   python manage.py runserver
   ```

2. **Open Login URL**
   - http://localhost:8000/auth/student/login/

3. **Enter Credentials**
   - Username: `student_test`
   - Password: `StudentTest1234`

4. **Verify Redirect**
   - Should go to `/dashboard/student/`

5. **Test Role Protection**
   - Try accessing `/dashboard/admin/`
   - Should show "Access Denied"

## How Authentication Works

```
1. User enters username/password on login form
   ↓
2. JavaScript sends to API endpoint (/api/auth/login/)
   ↓
3. API validates credentials against database
   ↓
4. If valid, returns token + user data
   ↓
5. JavaScript stores token in LocalStorage
   ↓
6. Checks user role
   ↓
7. Redirects to appropriate dashboard (/dashboard/{role}/)
   ↓
8. Dashboard view checks if user is authenticated + has correct role
   ↓
9. If yes, renders dashboard template
   ↓
10. If no, shows error or redirects to login
```

## Security Features

🔒 **Password Hashing** - Industry-standard Django hashing  
🔒 **Token Authentication** - Secure API token system  
🔒 **CSRF Protection** - Protected form submissions  
🔒 **Role-Based Access** - Decorator-based enforcement  
🔒 **Login Tracking** - All login attempts logged  
🔒 **Session Management** - Tokens deleted on logout  

## Testing Checklist

- [ ] Admin login works at `/auth/admin/login/`
- [ ] Coordinator login works at `/auth/coordinator/login/`
- [ ] Student login works at `/auth/student/login/`
- [ ] Each redirects to correct dashboard
- [ ] Wrong role cannot access other dashboards
- [ ] Logout clears session and redirects
- [ ] Unauthenticated users can't access dashboards
- [ ] API endpoints return proper responses

## Useful Commands

```bash
# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser

# Clear auth system
python manage.py flush

# View database
python manage.py dbshell

# See all users
python manage.py shell
>>> from apps.core.models import User
>>> User.objects.all().values('username', 'role')
```

---

## 🎉 Ready to Test!

The authentication system is **fully implemented and operational**.  
Use the test credentials above to verify everything works.
