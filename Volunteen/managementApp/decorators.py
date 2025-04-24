from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def donation_manager_required(view_func):
    """
    Decorator for views that checks that the user is logged in and belongs
    to the DonationManager group, raising a PermissionDenied error if not.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.groups.filter(name="DonationManager").exists():
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You do not have permission to access this page.")
    return _wrapped_view


def campaign_manager_required(view_func):
    """
    Decorator for views that ensures the user is logged in and
    belongs to the CampaignManager group.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.groups.filter(name="CampaignManager").exists():
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You do not have permission to access this page.")
    return _wrapped_view