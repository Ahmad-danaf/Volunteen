from django.shortcuts import redirect, render, get_object_or_404
from .forms import CreateUserForm, RedemptionForm, IdentifyChildForm
from django.contrib.auth.models import auth
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from .models import Task, Reward, Child, Mentor, Redemption, Shop
import requests
from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import redirect

@login_required
def logout_view(request):
    logout(request)
    return redirect('two_factor:login')

@login_required
def home_redirect(request):
    if request.user.groups.filter(name='Children').exists():
        return redirect('child_home')
    elif request.user.groups.filter(name='Mentors').exists():
        return redirect('mentor_home')
    elif request.user.groups.filter(name='Shops').exists():
        return redirect('shop_home')
    else:
        # Redirect to a default page if the user is not in any of the specified groups
        return redirect('default_home')
    
    
def default_home(request):
    return HttpResponse("Home")

@login_required
def child_home(request):
    child = Child.objects.get(user=request.user)
    return render(request, 'child_home.html', {'child': child})

@login_required
def mentor_home(request):
    mentor = Mentor.objects.get(user=request.user)
    tasks = Task.objects.all()

    if request.method == 'POST':
        child_identifiers = request.POST.get('child_identifiers', '').split(',')
        task_id = request.POST.get('task')

        if task_id:
            try:
                task = Task.objects.get(id=task_id)
                mentor.assign_points_to_children(child_identifiers, task)
                messages.success(
                    request,
                    f"Points successfully assigned for task '{task.title}' to children: {', '.join(child_identifiers)}"
                )
            except Task.DoesNotExist:
                messages.error(request, f"Task with id {task_id} does not exist.")

        return redirect('mentor_home') 
    return render(request, 'mentor_home.html', {'mentor': mentor, 'tasks': tasks})

@login_required
def mentor_points_summary(request):
    children = Child.objects.all().order_by('-points')
    return render(request, 'mentor_points_summary.html', {'children': children})

def list_view(request):
    tasks = []
    url = 'https://api.sheety.co/376dda55bc979408041d482218850b94/volunteenTasks/sheet1'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tasks = data['sheet1']

    return render(request, 'list_tasks.html', {'tasks': tasks})

def reward(request):
    rewards = Reward.objects.all()
    return render(request, 'reward.html', {'rewards': rewards})

@login_required
def redeem_points(request):
    if request.method == 'POST':
        if 'identifier' in request.POST:
            id_form = IdentifyChildForm(request.POST)
            if id_form.is_valid():
                identifier = id_form.cleaned_data['identifier']
                secret_code = id_form.cleaned_data['secret_code']
                try:
                    child = Child.objects.get(identifier=identifier, secret_code=secret_code)
                    return render(request, 'shop_redeem_points.html', {'child': child, 'id_form': id_form, 'points_form': RedemptionForm()})
                except Child.DoesNotExist:
                    return HttpResponse('Invalid identifier or secret code', status=400)
        else:
            points_form = RedemptionForm(request.POST)
            if points_form.is_valid():
                points = points_form.cleaned_data['points']
                child_id = request.POST['child_id']
                child = get_object_or_404(Child, id=child_id)
                if child.points >= points:
                    child.subtract_points(points)
                    shop = Shop.objects.get(user=request.user)
                    Redemption.objects.create(child=child, points_used=points, shop=shop)
                    return HttpResponse('Redemption successful')
                else:
                    return HttpResponse('Not enough points', status=400)
    else:
        id_form = IdentifyChildForm()
        points_form = RedemptionForm()

    return render(request, 'shop_redeem_points.html', {'id_form': id_form, 'points_form': points_form})

@login_required
def shop_home(request):
    if not request.user.groups.filter(name='Shops').exists():
         return redirect('two_factor:login')

    shop = Shop.objects.get(user=request.user)
    recent_redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')[:10]

    return render(request, 'shop_home.html', {
        'shop': shop,
        'recent_redemptions': recent_redemptions,
    })
