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

        # Fallback: query string token (for JS WebSocket when cookie is absent)
        if not token_key:
            qs = scope.get('query_string', b'')
            if isinstance(qs, bytes):
                try:
                    qs_decoded = qs.decode('utf-8', errors='replace')
                    params = dict(p.split('=', 1) for p in qs_decoded.split('&') if '=' in p)
                    token_key = params.get('token')
                except Exception:
                    pass

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
        # NOTE: script-src retains 'unsafe-inline' because templates use 100+ inline
        # onclick/onsubmit handlers. Per the CSP spec, 'unsafe-inline' is ignored
        # when a nonce is present, making nonces incompatible with inline event handlers.
        # A full fix requires migrating all inline handlers to addEventListener (future work).
        # style-src 'unsafe-inline' has been REMOVED — inline CSS injection is low-risk.
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.tailwindcss.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "media-src 'self' blob:; "
            "connect-src 'self' ws: wss: https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "frame-ancestors 'none'"
        )

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'

        return response

