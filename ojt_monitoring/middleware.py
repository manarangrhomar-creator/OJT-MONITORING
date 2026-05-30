"""
Custom middleware for OJT Monitoring System
"""


class CSRFExemptMiddleware:
    """
    Exempt API endpoints from CSRF protection.
    This allows token-based authentication for API calls.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Exempt all /api/ endpoints from CSRF by marking them
        if request.path.startswith('/api/'):
            request.csrf_processing_done = True
        
        response = self.get_response(request)
        return response
