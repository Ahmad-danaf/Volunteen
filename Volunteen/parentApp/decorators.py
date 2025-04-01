from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from childApp.models import Child
from django.http import HttpResponse

def parent_child_subscription_required(view_func):
    """
    Decorator for parent views where a child_id is passed in the URL.
    - Ensures the user is logged in
    - Ensures the child belongs to the parent
    - Ensures the child has an active subscription
    If not, redirects to inactive page.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        # Make sure parent is accessing their own child
        child_id = kwargs.get('child_id')
        child = get_object_or_404(Child, id=child_id)

        # Optional: extra check that this user is a parent
        parent = getattr(user, 'parent', None)
        if not parent or child.parent != parent:
           return HttpResponse("You are not authorized to access this page")

        # Check for subscription
        subscription = getattr(child, 'subscription', None)
        if subscription and subscription.is_active():
            return view_func(request, *args, **kwargs)

        # No active subscription -> redirect
        return redirect('parentApp:inactive_home', child_id=child.id)

    return _wrapped_view