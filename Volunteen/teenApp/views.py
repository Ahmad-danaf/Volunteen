from email import message
from django.shortcuts import redirect, render

from .forms import CreateUserForm

from django.contrib.auth.models import auth


from django.contrib.auth.decorators import login_required
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from .models import Task, Reward
from django.shortcuts import get_object_or_404, render, redirect
from .models import Reward, Child
from django.contrib.auth.decorators import login_required




@login_required
def redeem_reward(request, reward_id):
    reward = get_object_or_404(Reward, pk=reward_id)
    child = request.user.child  # Ensure this relation exists in your User model
    
    if request.method == 'POST':
        if child.points >= reward.points_required:
            points_used = reward.points_required  # The amount of points deducted
            child.points -= points_used
            child.save()
            # Add completed tasks details if relevant
            
            # Here, calculate the remaining points
            points_remaining = child.points
            current_datetime = datetime.now()
            # Pass 'points_remaining' in the context
            return render(request, 'success-points.html', {
                 'reward_title': reward.title,
                'points_used': points_used,
                'points_remaining': points_remaining,
                'current_datetime': current_datetime
            })
        else:
            # If the child doesn't have enough points, render the 'not-enough-points' template
            return render(request, 'not-enough-points.html', {
                'points_required': reward.points_required,
                'current_points': child.points
            })
    
    # If the request method is not POST, render the 'confirm-reward' page
    return render(request, 'confirm-reward.html', {'reward': reward})



@login_required
def do_task(request, task_id):
    task = get_object_or_404(Reward, pk=task_id)
    child = request.user.child  # Ensure this relation exists in your User model
    
    if request.method == 'POST':
            points_used = task.points  # The amount of points deducted
            child.points += points_used
            child.save()
            # Add completed tasks details if relevant
            
            # Here, calculate the remaining points
            points_remaining = child.points
            current_datetime = datetime.now()
            # Pass 'points_remaining' in the context
            return render(request, 'success-points.html', {
                'task_title': task.title,
                'points_used': points_used,
                'points_remaining': points_remaining,
                'current_datetime': current_datetime
            })
    return render(request, 'confirm-task.html', {'task': task})





# Create your views here.
def home(request):
    return redirect('two_factor:login')

def index(request):
    return render(request,'index.html')

from django.shortcuts import render, redirect
from django.contrib.auth import login  # אם אתה רוצה להתחבר את המשתמש מיד אחרי ההרשמה
from .forms import CreateUserForm
from .models import Child

def register(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()  # שמור את המשתמש וקבל את האובייקט שנוצר
            Child.objects.create(user=user)  # צור אובייקט Child חדש עבור המשתמש החדש
            login(request, user)  # אופציונלי - התחבר את המשתמש מיד לאחר ההרשמה
            return redirect("two_factor:login")
    context = {'form': form}
    return render(request, 'register.html', context=context)

def dashboard(request):

    return render(request, 'dashboard.html')
def list_view(request):
    tasks = Task.objects.filter(completed=False)
    return render(request, 'list_tasks.html', {'tasks': tasks})

def reward(request):
    # Retrieve all rewards from the database
    rewards = Reward.objects.all()

    # Pass rewards to the template for rendering
    return render(request, 'reward.html', {'rewards': rewards})
def adam_profile(request):
    return render(request, 'adam_profile.html')


def delete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.delete()
    return redirect('list')  # Replace 'list' with the actual name of your task list view

def complete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.completed = True
    task.save()
    return redirect('list')  # Replace 'list' with the actual name of your task list view
