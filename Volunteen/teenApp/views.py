from django.shortcuts import redirect, render, get_object_or_404
from .forms import RedemptionForm, IdentifyChildForm, TaskImageForm 
from django.contrib.auth.models import auth
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task, Reward, Child, Mentor, Redemption, Shop
import requests
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout
from .forms import IdentifyChildForm
from .forms import RedemptionForm
from datetime import datetime
from django.shortcuts import redirect
import random
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.templatetags.static import static
from django.contrib.staticfiles.storage import staticfiles_storage


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
    available_tasks = get_all_tasks()  # Fetch tasks from Google Sheets

    if request.method == 'POST':
        child_identifiers = request.POST.get('child_identifiers', '').split(',')
        task_id = request.POST.get('task')

        if task_id:
            # Check if task already exists in the database, otherwise create it
            task_data = next((task for task in available_tasks if task['taskId'] == int(task_id)), None)
            if task_data:
                # Convert deadline to YYYY-MM-DD format
                try:
                    deadline_str = task_data['deadline']
                    deadline = datetime.strptime(deadline_str, "%d/%m/%Y").date()
                except ValueError:
                    messages.error(request, f"Invalid date format for task deadline: {deadline_str}")
                    return redirect('mentor_home')

                task, created = Task.objects.get_or_create(
                    task_id=task_data['taskId'],
                     defaults={
                        'title': task_data.get('title', 'Untitled Task'),
                        'description': task_data.get('description', 'No description available'),
                        'points': task_data.get('points', 0),
                        'duration': task_data.get('duration', 'Not specified'),
                        'deadline': deadline, 
                        'additional_details': task_data.get('adddetails', 'No additional details')
                    }
                )

                # Assign points and mark task as completed for each child
                for identifier in child_identifiers:
                    try:
                        child = Child.objects.get(identifier=identifier)
                        child.add_points(task.points)
                        task.completed_by.add(child)
                        child.completed_tasks.add(task)
                        messages.success(
                    request,
                    f"Points successfully assigned for task '{task.title}' to child: {child.user.first_name} {child.user.last_name}"
                    )
                    except Child.DoesNotExist:
                        messages.error(request, f"Child with identifier {identifier} does not exist.")

               
            else:
                messages.error(request, f"Task with id {task_id} does not exist in the available tasks.")

        return redirect('mentor_home')

    return render(request, 'mentor_home.html', {'mentor': mentor, 'tasks': available_tasks})

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
                    child.secret_code=get_random_digits()
                    child.save()
                    return render(request, 'shop_redeem_points.html', {'child': child, 'id_form': id_form, 'points_form': RedemptionForm()})
                except Child.DoesNotExist:
                    return render(request, 'shop_invalid_identifier.html')
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
                    return render(request, 'shop_redemption_success.html', {'child': child, 'points_used': points})
                else:
                    return render(request, 'shop_not_enough_points.html')
    else:
        id_form = IdentifyChildForm()
        points_form = RedemptionForm()

    return render(request, 'shop_redeem_points.html', {'id_form': id_form, 'points_form': points_form})

@login_required
def shop_home(request):
    shop = Shop.objects.get(user=request.user)
    start_of_month = now().replace(day=1)
    redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
    points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
    points_left_to_redeem = max(0, shop.max_points - points_used_this_month)

    context = {
        'shop': shop,
        'points_used_this_month': points_used_this_month,
        'points_left_to_redeem': points_left_to_redeem,
    }
    return render(request, 'shop_home.html', context)

def get_random_digits(n=3):
    return ''.join(str(random.randint(0, 9)) for _ in range(n))

def get_all_tasks():
    tasks = []
    url = 'https://api.sheety.co/376dda55bc979408041d482218850b94/volunteenTasks/sheet1'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        tasks = data['sheet1']
        
    return tasks

@login_required
def mentor_completed_tasks_view(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        task = Task.objects.get(id=task_id)
        form = TaskImageForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            form.save()
        return redirect('mentor_completed_tasks')

    tasks = Task.objects.all()
    task_data = []
    for task in tasks:
        task_info = {
            'task': task,
            'form': TaskImageForm(instance=task),
            'completed_by': task.completed_by.all(),
            'completed_count': task.completed_by.count(),
        }
        task_data.append(task_info)

    return render(request, 'mentor_completed_tasks_view.html', {'task_data': task_data})

@login_required
def shop_redemption_history(request):
    shop = request.user.shop
    redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')
    monthly_redemptions = (
        redemptions.annotate(month=TruncMonth('date_redeemed'))
                   .values('month')
                   .annotate(total_points=Sum('points_used'))
                   .annotate(max_points=F('shop__max_points')) 
                   .order_by('-month')
    )

    last_redemptions = redemptions[:10]  # Get the last 10 redemptions
    

    context = {
        'shop': shop,
        'monthly_redemptions': monthly_redemptions,
        'recent_redemptions': last_redemptions,
    }
    return render(request, 'shop_redemption_history.html', context)


def rewards_view(request):
    # Prefetch related rewards to minimize database hits
    shops = Shop.objects.prefetch_related('rewards').all()

    # Prepare a new list to hold shops with modified data
    shops_with_images = []
    for shop in shops:
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        # Assign default image if none exists
        shop_image = shop.img if shop.img else None
        
        # Prepare rewards, assigning default images if necessary
        rewards_with_images = [
            {
                'title': reward.title,
                'img_url': reward.img if reward.img else static('images/logo.png'),
                'points' : reward.points_required
            }
            for reward in shop.rewards.all() if reward.points_required <= points_used_this_month
        ]
        
        # Append modified shop data to the list
        shops_with_images.append({
            'name': shop.name,
            'img': shop_image,
            'rewards': rewards_with_images,
            'used_points':points_used_this_month
        })

    context = {'shops': shops_with_images}
    return render(request, 'reward.html', context)


