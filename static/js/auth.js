/**
 * Authentication Utility Functions
 * Handles API calls for login, register, and logout
 * 
 * Security: Auth tokens are stored in httpOnly cookies (set by the server),
 * NOT in localStorage. Only non-sensitive user data is stored in localStorage.
 */

const API_BASE_URL = '/api/auth';
const USER_ROLE_KEY = 'user_role';
const USER_DATA_KEY = 'user_data';

/**
 * Store non-sensitive user data in localStorage (token is in httpOnly cookie)
 */
function storeAuthToken(token, user) {
    // Token is set as httpOnly cookie by the server — do NOT store in localStorage
    localStorage.setItem(USER_ROLE_KEY, user.role);
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
}

/**
 * Check if user is authenticated by calling /api/auth/me/
 * (httpOnly cookie is sent automatically)
 */
async function isAuthenticated() {
    try {
        const response = await fetch(`${API_BASE_URL}/me/`, {
            method: 'GET',
            credentials: 'same-origin',  // send cookies
        });
        return response.ok;
    } catch {
        return false;
    }
}

/**
 * Retrieve user role from localStorage
 */
function getUserRole() {
    return localStorage.getItem(USER_ROLE_KEY);
}

/**
 * Retrieve user data from localStorage
 */
function getUserData() {
    const userData = localStorage.getItem(USER_DATA_KEY);
    return userData ? JSON.parse(userData) : null;
}

/**
 * Clear authentication data from localStorage
 */
function clearAuthData() {
    localStorage.removeItem(USER_ROLE_KEY);
    localStorage.removeItem(USER_DATA_KEY);
}

/**
 * Make API request (cookies are sent automatically by browser)
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin',  // send httpOnly cookies
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const responseData = await response.json();

        if (!response.ok) {
            const message = responseData.detail
                || (responseData.non_field_errors && responseData.non_field_errors[0])
                || (responseData.email && responseData.email[0])
                || (responseData.password && responseData.password[0])
                || JSON.stringify(responseData);
            throw new Error(message);
        }

        return responseData;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Get CSRF token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Login user with email/ID and password
 */
async function login(identifier, password) {
    try {
        clearAuthData();
        const response = await apiRequest('/login/', 'POST', { identifier, password });
        
        if (response.token && response.user) {
            storeAuthToken(response.token, response.user);
            return response;
        }
        throw new Error('Invalid response from server');
    } catch (error) {
        console.error('Login failed:', error);
        throw error;
    }
}

/**
 * Register new user
 */
async function register(userData) {
    try {
        const response = await apiRequest('/register/', 'POST', userData);
        return response;
    } catch (error) {
        console.error('Registration failed:', error);
        throw error;
    }
}

/**
 * Logout user
 */
async function logout() {
    try {
        await apiRequest('/logout/', 'POST');
    } catch (error) {
        console.error('Logout API error:', error);
    } finally {
        clearAuthData();
        window.location.href = '/auth/logout/';
    }
}

/**
 * Redirect based on user role
 */
function redirectByRole(userRole) {
    const redirectMap = {
        'admin': '/dashboard/admin/',
        'coordinator': '/dashboard/coordinator/',
        'student': '/dashboard/student/',
    };

    const redirectUrl = redirectMap[userRole];
    if (redirectUrl) {
        window.location.href = redirectUrl;
    } else {
        window.location.href = '/';
    }
}

/**
 * Check authentication and redirect if not authenticated
 */
async function requireAuth() {
    if (!(await isAuthenticated())) {
        window.location.href = '/auth/login/';
    }
}

/**
 * Check if current user has a specific role
 */
function hasRole(role) {
    return getUserRole() === role;
}

function showAlert(message) {
    return Swal.fire({
        icon: 'info',
        text: message,
        confirmButtonColor: '#11693A',
        confirmButtonText: 'OK',
    });
}

/**
 * Protect dashboard access based on role
 */
async function protectDashboard(requiredRole) {
    if (!(await isAuthenticated())) {
        window.location.href = '/auth/login/';
        return false;
    }

    const userRole = getUserRole();
    if (userRole !== requiredRole) {
        showAlert('Access Denied: You do not have permission to view this page.');
        window.location.href = '/';
        return false;
    }

    return true;
}
