from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class CookieTokenAuthentication(TokenAuthentication):
    """
    Token authentication via httpOnly cookie.
    
    Reads the auth token from an httpOnly cookie instead of localStorage,
    preventing XSS from stealing the token.
    
    Falls back to the Authorization header for API clients.
    Enforces token expiry via TOKEN_EXPIRED_AFTER_SECONDS.
    """
    keyword = 'Token'

    def authenticate(self, request):
        # Try cookie first
        token_key = request.COOKIES.get('auth_token')
        if token_key:
            return self.authenticate_credentials(token_key)
        
        # Fallback to Authorization header (for API clients, WebSocket, etc.)
        return super().authenticate(request)

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')
        
        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')
        
        # Enforce token expiry
        expiry_seconds = getattr(settings, 'TOKEN_EXPIRED_AFTER_SECONDS', None)
        if expiry_seconds is not None:
            expiry_time = token.created + timedelta(seconds=expiry_seconds)
            if timezone.now() > expiry_time:
                token.delete()
                raise AuthenticationFailed('Token has expired. Please log in again.')
        
        return (token.user, token)
