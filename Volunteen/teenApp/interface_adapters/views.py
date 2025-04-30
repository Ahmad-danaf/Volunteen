from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from teenApp.entities.task import Task
from django.http import HttpResponse
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.conf import settings

@login_required
def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL) 
def landing_page(request):
    return render(request, 'landing_page.html')
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def home_redirect(request):
    user = request.user
    # If the user is a superuser, redirect to admin dashboard.
    if user.is_superuser:
        return redirect('admin:index')
    
    user_groups = list(user.groups.values_list('name', flat=True))
    
    if 'Children' in user_groups:
        return redirect('childApp:child_home')
    elif 'Mentors' in user_groups:
        return redirect('mentorApp:mentor_home')
    elif 'Shops' in user_groups:
        return redirect('shopApp:shop_home')
    elif 'Parents' in user_groups:
        return redirect('parentApp:parent_home')
    elif 'Institutions' in user_groups:
        return redirect('institutionApp:institution_home')
    elif 'DonationManager' in user_groups:
        return redirect('managementApp:donation_manager_dashboard')
    elif 'CampaignManager' in user_groups:
        return redirect('managementApp:campaign_manager_home')
    else:
        return redirect('admin:index')

def default_home(request):
    return HttpResponse("Home")


@login_required
def list_view(request):
    tasks = Task.objects.all()
    return render(request, 'list_tasks.html', {'tasks': tasks})

def csrf_failure_view(request, reason=""):
    print("CSRF Failure:", reason)  
    html = render_to_string('errors/csrf_failure.html')
    return HttpResponseForbidden(html)


