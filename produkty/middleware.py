from django.utils.cache import add_never_cache_headers

class NoCacheMiddleware:
    """
    Middleware that adds headers to prevent caching of pages 
    if the user is authenticated. This helps prevent issues where 
    users log out and use the 'Back' button to see cached authenticated pages.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Apply no-cache headers to all responses where the user is authenticated
        # Or, alternatively, apply it to all pages. To be safe with the app logic, we apply it if user is authenticated.
        if hasattr(request, 'user') and request.user.is_authenticated:
            add_never_cache_headers(response)
        # We also want to apply it to the login page so it's always fresh.
        elif request.path.startswith('/login/'):
            add_never_cache_headers(response)
            
        return response
