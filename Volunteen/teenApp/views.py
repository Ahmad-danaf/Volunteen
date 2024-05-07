from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task, Reward, Child, Mentor, Redemption, Shop
import requests
from django.http import HttpResponse
from django.contrib.auth import logout
from .forms import IdentifyChildForm
from .forms import RedemptionForm
from datetime import datetime

@login_required
def logout_view(request):
    # Handles user logout and redirects to login page
    logout(request)
    return redirect('two_factor:login')

@login_required
def home_redirect(request):
    # Redirects users to different home pages based on their group
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
    # Default home page response
    return HttpResponse("Home")


@login_required
def child_home(request):
    # Child home page view
    child = Child.objects.get(user=request.user)

    greetings = {
        0: f"Wishing you a strong start to the week to collect points!",  # Sunday
        1: f"It's Monday! Stay positive and keep working towards your goals!",
        2: f"It's Tuesday! Keep pushing forward and make today count!",
        3: f"It's Wednesday! You're halfway through the week, stay focused!",
        4: f"It's Thursday! Almost there, finish the week strong!",
        5: f"Happy Friday! Enjoy your day and make the most out of it!",  # Friday
        6: f"It's Saturday! Relax and recharge for the upcoming week!",
    }
    
    today = datetime.today().weekday()
    greeting = greetings.get(today, f"Hey {child.user.username}, have a great day!")
    return render(request, 'child_home.html', {'child': child, 'greeting': greeting})

@login_required
def redemption_history(request):
    child = Child.objects.get(user=request.user)
    redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')
    return render(request, 'redemption_history.html', {'redemptions': redemptions})

@login_required
def completed_tasks(request):
    child = Child.objects.get(user=request.user)
    return render(request, 'completed_tasks.html', {'child': child})
@login_required
def mentor_home(request):
    # Mentor home page view
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
    # Fetch children and their last three tasks
    children = Child.objects.all().order_by('-points')

    # Annotate each child with their last three completed tasks
    for child in children:
        # Update the ordering to use a valid field
        child.last_three_tasks = child.completed_tasks.filter(completed=True).order_by('-id')[:3]

    return render(request, 'mentor_points_summary.html', {'children': children})

def list_view(request):
    # Retrieves and lists tasks from an external API
    tasks = []
    url = 'https://api.sheety.co/376dda55bc979408041d482218850b94/volunteenTasks/sheet1'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tasks = data['sheet1']

    return render(request, 'list_tasks.html', {'tasks': tasks})

def reward(request):
    # Displays available rewards
    rewards = Reward.objects.all()
    return render(request, 'reward.html', {'rewards': rewards})

@login_required
def redeem_points(request):
    # Handles points redemption process for children
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
    # Shop home page view
    if not request.user.groups.filter(name='Shops').exists():
         return redirect('two_factor:login')

    shop = Shop.objects.get(user=request.user)
    recent_redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')[:10]

    return render(request, 'shop_home.html', {
        'shop': shop,
        'recent_redemptions': recent_redemptions,
    })
