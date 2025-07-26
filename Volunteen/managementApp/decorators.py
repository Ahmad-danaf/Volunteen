from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def user_in_group(user, *group_names):
    """
    Checks if a user belongs to any of the given groups.
    """
    return user.is_authenticated and user.groups.filter(name__in=group_names).exists()

def donation_manager_required(view_func):
    """
    Decorator for views that allow access to DonationManager or SuperAdmin.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if user_in_group(request.user, "DonationManager", "SuperAdmin"):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You do not have permission to access this page.")
    return _wrapped_view


def campaign_manager_required(view_func):
    """
    Decorator for views that allow access to CampaignManager or SuperAdmin.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if user_in_group(request.user, "CampaignManager", "SuperAdmin"):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You do not have permission to access this page.")
    return _wrapped_view


def superadmin_required(view_func):
    """
    Decorator for views accessible only to SuperAdmin.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if user_in_group(request.user, "SuperAdmin"):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied("You do not have permission to access this page.")
    return _wrapped_view