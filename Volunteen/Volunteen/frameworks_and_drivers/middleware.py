from django.http import JsonResponse
from django.conf import settings


class ApiKeyMiddleware:
    """
    Middleware to validate API Key for every request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        api_key = request.headers.get('X-API-Key')  # Header key is case-insensitive
        if not api_key or api_key != settings.X_API_KEY:
            return JsonResponse({'error': 'Invalid or missing API Key'}, status=403)
        return self.get_response(request)
