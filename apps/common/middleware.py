"""
Custom middleware for iframe support and other enhancements.
"""


class AllowFrameMiddleware:
    """Allow the application to be embedded in iframes by removing X-Frame-Options restrictions."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        # Remove X-Frame-Options header to allow iframe embedding
        # (already removed XFrameOptionsMiddleware, but explicitly set to be safe)
        response['X-Frame-Options'] = 'ALLOWALL'
        return response
