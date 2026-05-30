/**
 * Authentication Utility Functions
 * Handles API calls for login, register, and logout
 */

const API_BASE_URL = '/api/auth';
const AUTH_TOKEN_KEY = 'auth_token';
const USER_ROLE_KEY = 'user_role';
const USER_DATA_KEY = 'user_data';

/**
 * Store authentication token and user data in localStorage
 */
function storeAuthToken(token, user) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(USER_ROLE_KEY, user.role);
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
}

/**
 * Retrieve authentication token from localStorage
 */
function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
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
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!getAuthToken();
}

/**
 * Clear authentication data from localStorage
 */
function clearAuthData() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_ROLE_KEY);
    localStorage.removeItem(USER_DATA_KEY);
}

/**
 * Make API request with authentication
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const token = getAuthToken();
    const isAuthEndpoint = endpoint === '/login/' || endpoint === '/register/';
    if (token && !isAuthEndpoint) {
        options.headers['Authorization'] = `Token ${token}`;
    }

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const responseData = await response.json();

        if (!response.ok) {
            throw new Error(responseData.detail || JSON.stringify(responseData));
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
 * Login user with username and password
 */
async function login(username, password) {
    try {
        // Clear any stale token before attempting login
        clearAuthData();
        const response = await apiRequest('/login/', 'POST', { username, password });
        
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
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/auth/login/';
    }
}

/**
 * Check if current user has a specific role
 */
function hasRole(role) {
    return getUserRole() === role;
}

/**
 * Protect dashboard access based on role
 */
function protectDashboard(requiredRole) {
    if (!isAuthenticated()) {
        window.location.href = '/auth/login/';
        return false;
    }

    const userRole = getUserRole();
    if (userRole !== requiredRole) {
        alert('Access Denied: You do not have permission to view this page.');
        window.location.href = '/';
        return false;
    }

    return true;
}
