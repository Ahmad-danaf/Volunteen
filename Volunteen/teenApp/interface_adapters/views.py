from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from teenApp.entities.task import Task
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.http import require_POST
from teenApp.utils.PersonalInfoUtils import PersonalInfoUtils
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
    elif 'SuperAdmin' in user_groups:
        return redirect('managementApp:superadmin_dashboard')
    elif user.is_superuser:
        return redirect('admin:index')
    else:
        return redirect('teenApp:home_redirect')
    

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

@login_required
def phone_update_page(request):
    return render(request, 'teenApp/update_phone.html')


@require_POST
@login_required
def update_phone_number(request):
    phone = request.POST.get('phone') or request.body.decode()  

    if not phone:
        return JsonResponse({'success': False, 'error': 'Missing phone number'}, status=400)

    updated = PersonalInfoUtils.update_user_phone(request.user, phone)

    if updated:
        return JsonResponse({'success': True, 'message': 'Phone number updated'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid phone number'}, status=400)