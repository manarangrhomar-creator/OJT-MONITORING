from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        return Token.objects.select_related('user').get(key=token_key).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token_key = None

        # Try cookie first (httpOnly, sent automatically by browser)
        cookies = scope.get('cookies', {})
        if isinstance(cookies, dict):
            token_key = cookies.get('auth_token')

        if token_key:
            scope['user'] = await get_user_from_token(token_key)
        else:
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)


class SecurityHeadersMiddleware:
    """Add security headers to all HTTP responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy
        # NOTE: 'unsafe-inline' is required because templates use 300+ inline
        # onclick/onsubmit handlers. Per the CSP spec, 'unsafe-inline' is ignored
        # when a nonce is present, making nonces incompatible with inline event handlers.
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss: https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "frame-ancestors 'none'"
        )

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response

