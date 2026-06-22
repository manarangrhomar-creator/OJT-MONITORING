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
 * Show a custom alert modal (self-contained, creates DOM on first call)
 */
let _alertModalCreated = false;
function showAlert(message) {
    if (!_alertModalCreated) {
        const overlay = document.createElement('div');
        overlay.id = 'auth-alert-modal';
        overlay.className = 'hidden fixed inset-0 bg-black/50 z-[9999] flex items-center justify-center p-4';
        overlay.innerHTML = `
            <div class="bg-white rounded-2xl max-w-sm w-full p-6 shadow-2xl text-center border border-slate-100 transform scale-95 transition-all">
                <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                </div>
                <h3 class="text-lg font-black text-slate-800 mb-1">Notice</h3>
                <p id="auth-alert-message" class="text-xs text-slate-500 mb-6">${message}</p>
                <button type="button" id="auth-alert-ok" class="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition uppercase shadow-sm">OK</button>
            </div>`;
        document.body.appendChild(overlay);
        document.getElementById('auth-alert-ok').addEventListener('click', () => {
            document.getElementById('auth-alert-modal').classList.add('hidden');
        });
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.classList.add('hidden');
        });
        _alertModalCreated = true;
    }
    document.getElementById('auth-alert-message').textContent = message;
    document.getElementById('auth-alert-modal').classList.remove('hidden');
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
        showAlert('Access Denied: You do not have permission to view this page.');
        window.location.href = '/';
        return false;
    }

    return true;
}
