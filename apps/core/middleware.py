import base64
import secrets

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

        # Read token from httpOnly cookie (sent automatically by browser)
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
        # Generate per-request nonce for inline <script> tags (context_processor reads this)
        request.csp_nonce = base64.b64encode(secrets.token_bytes(16)).decode('ascii')

        response = self.get_response(request)

        nonce = request.csp_nonce
        # Content Security Policy
        # 'unsafe-inline' is required for ~200+ inline event handlers (onclick/onsubmit/onchange)
        # across templates and for inline styles (~550+ style="..." attributes).
        # Per CSP Level 3, 'unsafe-inline' is ignored when a nonce is present in script-src.
        # Removing nonce allows 'unsafe-inline' to take effect for inline event handlers.
        # The nonce context_processor is preserved (harmless) in case of future migration.
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com https://unpkg.com; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.tailwindcss.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "media-src 'self' blob:; "
            "connect-src 'self' ws: wss: https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://nominatim.openstreetmap.org; "
            "frame-ancestors 'none'"
        )

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=(self)'

        return response

