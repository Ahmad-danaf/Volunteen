from django.shortcuts import redirect, render, get_object_or_404
from .forms import RedemptionForm, IdentifyChildForm, TaskImageForm, BonusPointsForm 
from django.contrib.auth.models import auth
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Task, Reward, Child, Mentor, Redemption, Shop
import requests
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout
from datetime import datetime
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.templatetags.static import static


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
    
    today = datetime.today().weekday()+1
    greeting = greetings.get(today, f"Hey {child.user.username}, have a great day!")
    
    new_tasks = child.assigned_tasks.filter(new_task=True, viewed=False)
    new_tasks_count = new_tasks.count()

    if request.method == 'POST' and 'close_notification' in request.POST:
        new_tasks.update(viewed=True)
        new_tasks.update(new_task=False)

    return render(request, 'child_home.html', {'child': child, 'greeting': greeting, 'new_tasks_count': new_tasks_count, 'new_tasks': new_tasks})

@login_required
def child_redemption_history(request):
    child = Child.objects.get(user=request.user)
    redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')
    return render(request, 'child_redemption_history.html', {'redemptions': redemptions})

@login_required
def child_completed_tasks(request):
    child = Child.objects.get(user=request.user)
    return render(request, 'child_completed_tasks.html', {'child': child})

@login_required
def mentor_home(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    tasks = Task.objects.filter(assigned_mentors=mentor)

    # עדכון סטטוס של משימות שהדדליין שלהן עבר
    for task in tasks:
        if task.is_overdue():
            task.completed = True
            task.save()

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(completed=True).count()
    open_tasks = total_tasks - completed_tasks
    efficiency_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

    children = []
    for child in mentor.children.all():
        completed = child.completed_tasks.count()
        assigned = child.assigned_tasks.count()
        efficiency = (completed / assigned) * 100 if assigned > 0 else 0
        performance_color = "#d4edda" if efficiency >= 75 else "#f8d7da" if efficiency < 50 else "#fff3cd"
        children.append({
            'child': child,
            'efficiency_rate': efficiency,
            'performance_color': performance_color,
        })

    context = {
        'mentor': mentor,
        'total_tasks': total_tasks,
        'open_tasks': open_tasks,
        'completed_tasks': completed_tasks,
        'efficiency_rate': efficiency_rate,
        'children': children,
        'tasks': tasks,  # הוספת המשימות לקונטקסט
    }
    return render(request, 'mentor_home.html', context)


@login_required
def mentor_children_details(request):
    mentor = Mentor.objects.get(user=request.user)
    children = mentor.children.all()
    return render(request, 'mentor_children_details.html', {'children': children})

@login_required
def shop_redeem_points(request):
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


@login_required
def mentor_completed_tasks_view(request):
    mentor = Mentor.objects.get(user=request.user)

    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        task = Task.objects.get(id=task_id)
        form = TaskImageForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            form.save()
        return redirect('mentor_completed_tasks_view')

    tasks = Task.objects.filter(assigned_mentors=mentor, completed=True)
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
                'points': reward.points_required
            }
            for reward in shop.rewards.all() if reward.points_required <= points_used_this_month
        ]
        
        # Append modified shop data to the list
        shops_with_images.append({
            'name': shop.name,
            'img': shop_image,
            'rewards': rewards_with_images,
            'used_points': points_used_this_month
        })

    context = {'shops': shops_with_images}
    return render(request, 'reward.html', context)

@login_required
def list_view(request):
    # Retrieves and lists tasks from the database
    tasks = Task.objects.all()
    return render(request, 'list_tasks.html', {'tasks': tasks})


@login_required
def mentor_active_list(request):
    mentor = Mentor.objects.get(user=request.user)
    tasks = Task.objects.filter(assigned_mentors=mentor)
    return render(request, 'list_tasks.html', {'tasks': tasks})

@login_required
def child_active_list(request):
    try:
        child = Child.objects.get(user=request.user)
        tasks = Task.objects.filter(assigned_children=child, completed=False)
        
        # Update tasks to mark them as not new
        tasks.update(new_task=False)
        
        return render(request, 'list_tasks.html', {'tasks': tasks})
    except Child.DoesNotExist:
        return render(request, 'list_tasks.html', {'error': 'You are not authorized to view this page.'})

    
@login_required
def mentor_task_list(request):
    mentor = Mentor.objects.get(user=request.user)
    tasks = Task.objects.filter(assigned_mentors=mentor)  
    return render(request, 'mentor_task_list.html', {'tasks': tasks})

@login_required
def assign_task(request, task_id):
    mentor = Mentor.objects.get(user=request.user)
    task = get_object_or_404(Task, id=task_id)
    children = mentor.children.all()

    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        for child_id in selected_children_ids:
            child = get_object_or_404(Child, id=child_id)
            task.assigned_children.add(child)
            task.new_task = True
            task.save()
        task.assigned_mentors.add(mentor)
        messages.success(request, f"Task '{task.title}' successfully assigned to selected children.")
        return redirect('mentor_task_list')

    return render(request, 'assign_task.html', {'task': task, 'children': children})

@login_required
def assign_points(request, task_id):
    mentor = Mentor.objects.get(user=request.user)
    task = get_object_or_404(Task, id=task_id)
    children = mentor.children.filter(id__in=task.assigned_children.values_list('id', flat=True))

    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        for child_id in selected_children_ids:
            child = get_object_or_404(Child, id=child_id)
            child.add_points(task.points)
            task.completed_by.add(child)
        messages.success(request, f"Points successfully assigned for task '{task.title}' to selected children.")
        return redirect('points_assigned_success', task_id=task.id)

    return render(request, 'assign_points.html', {'task': task, 'children': children})

@login_required
def points_assigned_success(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    children = task.completed_by.all()
    return render(request, 'points_assigned_success.html', {'task': task, 'children': children})

@login_required
def child_points_history(request):
    child = Child.objects.get(user=request.user)
    tasks = child.tasks_completed.all().order_by('-id')  # Assuming tasks_completed is the correct related name
    return render(request, 'child_points_history.html', {'child': child, 'tasks': tasks})


from django.shortcuts import render, redirect
from .forms import BonusPointsForm
from .models import Task, Child

def assign_bonus(request):
    if request.method == 'POST':
        form = BonusPointsForm(request.POST)
        if form.is_valid():
            task = form.cleaned_data['task']
            child = form.cleaned_data['child']
            bonus_points = form.cleaned_data['bonus_points']
            
            # הוספת הבונוס לנקודות של הילד
            child.points += bonus_points
            child.save()
            
            # שמירת המידע שהילד קיבל בונוס עבור המשימה
            child.completed_tasks.add(task)
            
            return redirect('mentor_home')
    else:
        form = BonusPointsForm()
    
    return render(request, 'assign_bonus.html', {'form': form})