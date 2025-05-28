from django.utils import timezone
from datetime import timedelta

class LastActivityMiddleware:
    """
    Middleware to update the 'last_activity' field in PersonalInfo for authenticated users.
    It handles all edge cases gracefully and does not crash the request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            user = getattr(request, "user", None)
            
            if user and user.is_authenticated:
                personal_info = getattr(user, 'personal_info', None)

                if personal_info:
                    now = timezone.now()
                    last = personal_info.last_activity

                    if not last or (now - last) > timedelta(seconds=60):
                        personal_info.last_activity = now
                        personal_info.save(update_fields=['last_activity'])

        except Exception:
            pass  # Fail silently to avoid breaking requests

        return response
