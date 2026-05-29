# OJT Monitoring - Full Authentication System Implementation

## Overview
A complete authentication system has been implemented connecting frontend forms to backend API with role-based access control and token authentication.

## What's Been Implemented

### 1. **Backend Authentication API** ✅
- **Token-Based Authentication**: Uses Django REST Framework Token Authentication
- **Endpoints**:
  - `POST /api/auth/register/` - Register new user
  - `POST /api/auth/login/` - Login and receive authentication token
  - `POST /api/auth/logout/` - Logout (requires token)
  - `GET /api/auth/me/` - Get current user info (requires token)
  - `POST /api/auth/change_password/` - Change password (requires token)

- **Login Attempt Tracking**: Records successful and failed login attempts with IP and user agent

### 2. **Frontend Authentication JavaScript** ✅
**File**: `/static/js/auth.js`

**Core Functions**:
- `login(username, password)` - Authenticate user and store token
- `logout()` - Clear authentication and redirect to home
- `register(userData)` - Register new user
- `isAuthenticated()` - Check if user is logged in
- `getUserRole()` - Get user's role
- `redirectByRole(role)` - Redirect to appropriate dashboard based on role
- `protectDashboard(role)` - Protect dashboard access

**Features**:
- Token-based authentication
- LocalStorage for session persistence
- CSRF token handling
- Automatic role-based redirects

### 3. **Updated Login Forms** ✅
**Files**:
- `/templates/coordinator_login.html`
- `/templates/ojtstudent_login.html`
- `/templates/admin_login.html`

**Features**:
- Form validation against API
- Error messages display
- Loading indicators
- Role verification (prevents unauthorized access)
- Password visibility toggle
- Success redirection based on role

### 4. **Protected Dashboard Views** ✅
**File**: `/apps/core/dashboard_views.py`

**Protection Mechanism**:
- `@role_required(role)` decorator ensures only authenticated users with the correct role access dashboards
- Automatic redirect to login if not authenticated
- HTTP 403 Forbidden if wrong role

**Protected Routes**:
- `/dashboard/admin/` → Admin only
- `/dashboard/coordinator/` → Coordinator only
- `/dashboard/student/` → Student only
- `/dashboard/approval/` → Admin only

### 5. **Role-Based Access Control (RBAC)** ✅

**User Roles**:
1. **admin** - System administrator access
2. **coordinator** - OJT Coordinator access
3. **student** - OJT Student access

**Access Rules**:
- Each dashboard is protected and checks user role
- Login redirects to appropriate dashboard based on role
- Failed role verification shows access denied message

### 6. **Session Management** ✅
- Token stored in browser LocalStorage
- User role stored for quick access checks
- User data available throughout session
- Logout clears all session data and tokens

### 7. **URL Configuration** ✅
**New URLs Added**:
```
/auth/login/                    - Login page
/auth/logout/                   - Logout endpoint
/dashboard/admin/               - Protected admin dashboard
/dashboard/coordinator/         - Protected coordinator dashboard
/dashboard/student/             - Protected student dashboard
/dashboard/approval/            - Protected approval dashboard
```

## User Registration Data Required

When registering, users must provide:
```json
{
  "username": "string (unique)",
  "email": "string (email format)",
  "first_name": "string",
  "last_name": "string",
  "password": "string (min 8 chars, alphanumeric)",
  "password2": "string (must match password)",
  "role": "admin|coordinator|student",
  "phone_number": "string (optional)"
}
```

## Testing the Authentication System

### Create a Test User (via Django Shell)
```python
python manage.py shell

from apps.core.models import User
from rest_framework.authtoken.models import Token

# Create a test student
user = User.objects.create_user(
    username='teststudent',
    email='test@isu.edu.ph',
    password='Test1234',
    first_name='Test',
    last_name='Student',
    role='student'
)

# Token is automatically created
token = Token.objects.get(user=user)
print(token.key)
```

### Test Login Via API
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teststudent", "password": "Test1234"}'
```

### Test Protected Dashboard
```javascript
// In browser console
fetch('/dashboard/student/')
  .then(r => r.text())
  .then(html => console.log(html))
```

## Frontend User Flow

### For Admin
1. Navigate to `/auth/admin/login/`
2. Enter username and password
3. System validates against database
4. If valid and role is 'admin', redirects to `/dashboard/admin/`
5. If invalid, shows error message

### For Coordinator
1. Navigate to `/auth/coordinator/login/`
2. Enter username and password
3. System validates against database
4. If valid and role is 'coordinator', redirects to `/dashboard/coordinator/`
5. If invalid, shows error message

### For Student
1. Navigate to `/auth/student/login/`
2. Enter username and password
3. System validates against database
4. If valid and role is 'student', redirects to `/dashboard/student/`
5. If invalid, shows error message

## Security Features Implemented

✅ **Password Hashing**: Django's built-in password hashing  
✅ **Token Authentication**: Secure token-based API auth  
✅ **CSRF Protection**: CSRF tokens for form submissions  
✅ **Role-Based Access**: Decorator-based access control  
✅ **Login Attempt Tracking**: Logs all login attempts  
✅ **Session Invalidation**: Tokens deleted on logout  
✅ **IP & User Agent Logging**: Tracks suspicious activity  

## Next Steps (Optional Enhancements)

1. **Register Forms Update**: Connect coordinator and student register forms to API
2. **Password Reset**: Implement forgot password with email verification
3. **Two-Factor Authentication**: Add 2FA for additional security
4. **Rate Limiting**: Implement rate limiting on login attempts
5. **OAuth Integration**: Add social login (Google, GitHub, etc.)
6. **Session Timeout**: Auto-logout after inactivity period

## Files Modified/Created

### Created:
- `/static/js/auth.js` - Authentication utility functions
- `/apps/core/dashboard_views.py` - Protected dashboard views

### Modified:
- `/apps/authentication/views.py` - Updated for token authentication
- `/ojt_monitoring/settings.py` - Added rest_framework.authtoken
- `/ojt_monitoring/urls.py` - Updated dashboard routes and added logout
- `/templates/coordinator_login.html` - Connected to API
- `/templates/ojtstudent_login.html` - Connected to API
- `/templates/admin_login.html` - Connected to API

## API Response Example

**Login Success**:
```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "username": "teststudent",
    "email": "test@isu.edu.ph",
    "first_name": "Test",
    "last_name": "Student",
    "full_name": "Test Student",
    "role": "student",
    "phone_number": null,
    "is_active": true,
    "created_at": "2026-05-29T..."
  },
  "token": "token_key_here"
}
```

**Login Failure**:
```json
{
  "non_field_errors": [
    "Invalid credentials."
  ]
}
```
