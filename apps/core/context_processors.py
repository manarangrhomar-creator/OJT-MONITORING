def csp_nonce(request):
    """Expose the CSP nonce stored on the request by SecurityHeadersMiddleware."""
    return {'csp_nonce': getattr(request, 'csp_nonce', '')}
