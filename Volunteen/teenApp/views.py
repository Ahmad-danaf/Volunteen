from email import message
from django.shortcuts import redirect, render
from .forms import CreateUserForm, RedemptionForm, IdentifyChildForm
from django.contrib.auth.models import auth
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from .models import Task, Reward
from django.shortcuts import get_object_or_404, render, redirect
from .models import Reward, Child, Redemption, Shop
from django.contrib.auth.decorators import login_required
import requests
from django.http import HttpResponse



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

# def list_view(request):
#     tasks = Task.objects.filter(completed=False)
#     return render(request, 'list_tasks.html', {'tasks': tasks})

def list_view(request):
    tasks = []
    url = 'https://api.sheety.co/376dda55bc979408041d482218850b94/volunteenTasks/sheet1'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tasks = data['sheet1']

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



@login_required
def redeem_points(request):
    if request.method == 'POST':
        if 'identifier' in request.POST:
            # Handle identifier form
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
            # Handle redemption form
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
def home_redirect(request):
    if request.user.groups.filter(name='Children').exists():
        return redirect('child_home')
    elif request.user.groups.filter(name='Mentors').exists():
        return redirect('mentor_home')
    elif request.user.groups.filter(name='Shops').exists():
        return redirect('shop_home')
    else:
        return redirect('two_factor:login')


@login_required
def shop_home(request):
    # Check if the user belongs to the Shops group
    if not request.user.groups.filter(name='Shops').exists():
         return redirect('two_factor:login')

    # Get the shop associated with the current user
    shop = Shop.objects.get(user=request.user)

    # Get recent redemptions for this shop
    recent_redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')[:10]

    return render(request, 'shop_home.html', {
        'shop': shop,
        'recent_redemptions': recent_redemptions,
    })
    
