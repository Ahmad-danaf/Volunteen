from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def child_subscription_required(view_func):
    """
    Decorator for views that require a logged-in child with an active subscription.
    Redirects to inactive page if subscription is missing or expired.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        child = getattr(user, 'child', None)

        if child:
            subscription = getattr(child, 'subscription', None)
            if subscription and subscription.is_active():
                return view_func(request, *args, **kwargs)
            
            # If subscription is not active
            return redirect('childApp:inactive_home', child_id=child.id)

        # No child attached to this user
        return redirect('childApp:inactive_home', child_id=-1)

    return _wrapped_view