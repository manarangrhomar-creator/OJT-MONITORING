"""
Custom middleware to exempt API endpoints from CSRF verification.
"""
from django.utils.decorators import decorator_from_middleware_with_args
from django.middleware.csrf import CsrfViewMiddleware as OriginalCsrfViewMiddleware


class CsrfExemptMiddleware:
    """Middleware to exempt API endpoints from CSRF token verification."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exempt API endpoints from CSRF
        if request.path.startswith('/api/'):
            request.csrf_processing_done = True
        
        response = self.get_response(request)
        return response
