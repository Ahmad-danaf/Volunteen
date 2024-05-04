from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from datetime import datetime
from .models import Task, Reward, Child, Mentor
from .forms import CreateUserForm

@login_required
def redeem_reward(request, reward_id):
    reward = get_object_or_404(Reward, pk=reward_id)
    child = request.user.child
    
    if request.method == 'POST':
        if child.points >= reward.points_required:
            points_used = reward.points_required
            child.points -= points_used
            child.save()
            points_remaining = child.points
            current_datetime = datetime.now()
            return render(request, 'success-points.html', {
                'reward_title': reward.title,
                'points_used': points_used,
                'points_remaining': points_remaining,
                'current_datetime': current_datetime
            })
        else:
            return render(request, 'not-enough-points.html', {
                'points_required': reward.points_required,
                'current_points': child.points
            })
    return render(request, 'confirm-reward.html', {'reward': reward})

@login_required
def do_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    child = request.user.child
    
    if request.method == 'POST':
        points_used = task.points
        child.points += points_used
        child.save()
        points_remaining = child.points
        current_datetime = datetime.now()
        return render(request, 'success-points.html', {
            'task_title': task.title,
            'points_used': points_used,
            'points_remaining': points_remaining,
            'current_datetime': current_datetime
        })
    return render(request, 'confirm-task.html', {'task': task})

@login_required
def home_redirect(request):
    if request.user.groups.filter(name='Children').exists():
        return redirect('child_home')
    elif request.user.groups.filter(name='Mentors').exists():
        return redirect('mentor_home')
    elif request.user.groups.filter(name='Shops').exists():
        return redirect('shop_home')
    else:
        return redirect('two_factor:login')

def child_home(request):
    child = Child.objects.get(user=request.user)
    return render(request, 'child_home.html', {'child': child})
from django.contrib import messages

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
                # Call the assign_points_to_children method of the Mentor model
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
    children = Child.objects.all().order_by('-points')  # Sort by points descending
    return render(request, 'mentor_points_summary.html', {'children': children})

def shop_home(request):
    return render(request, 'shop_home.html')


def index(request):
    return render(request, 'index.html')

def register(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            Child.objects.create(user=user)
            login(request, user)
            return redirect("two_factor:login")
    return render(request, 'register.html', {'form': form})

def dashboard(request):
    return render(request, 'dashboard.html')

def list_view(request):
    tasks = Task.objects.filter(completed=False)
    return render(request, 'list_tasks.html', {'tasks': tasks})

def reward(request):
    rewards = Reward.objects.all()
    return render(request, 'reward.html', {'rewards': rewards})

def adam_profile(request):
    return render(request, 'adam_profile.html')
