from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from teenApp.entities.task import Task
from django.http import HttpResponse
from django.contrib.auth import logout

@login_required
def logout_view(request):
    logout(request)
    return redirect('two_factor:login')
def landing_page(request):
    return render(request, 'landing_page.html')

@login_required
def home_redirect(request):
    if request.user.groups.filter(name='Children').exists():
        return redirect('childApp:child_home')
    elif request.user.groups.filter(name='Mentors').exists():
        return redirect('mentorApp:mentor_home')
    elif request.user.groups.filter(name='Shops').exists():
        return redirect('shopApp:shop_home')
    elif request.user.groups.filter(name='Parents').exists():
        return redirect('parentApp:parent_home')
    else:
        return redirect('admin:index')  
        


def default_home(request):
    return HttpResponse("Home")


@login_required
def list_view(request):
    tasks = Task.objects.all()
    return render(request, 'list_tasks.html', {'tasks': tasks})

