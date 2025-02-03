from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Parent
from childApp.models import Child
from teenApp.entities.task import Task
from django.shortcuts import get_object_or_404
from django.utils import timezone

@login_required
def parent_home(request):
    # Fetch the parent object
    parent = Parent.objects.get(user=request.user)
    
    # Fetch all children linked to the parent
    children = Child.objects.filter(parent=parent)
    
    # Fetch recent tasks and redemptions for each child
    for child in children:
        child.recent_tasks = Task.objects.filter(completed_by_children=child).order_by('-id')[:5]
        child.recent_redemptions = []  # Add logic for redemptions if applicable
    
    # Prepare summary statistics
    total_points = sum(child.points for child in children)
    total_children = children.count()
    
    # Prepare data for charts
    points_distribution = [child.points for child in children]
    task_completion = [child.completed_tasks.count() for child in children]
    
    context = {
        'parent': parent,
        'children': children,
        'total_points': total_points,
        'total_children': total_children,
        'points_distribution': points_distribution,
        'task_completion': task_completion,
    }
    
    return render(request, 'parent_home.html', context)

@login_required
def parent_stats(request):
    # Fetch the parent object
    parent = Parent.objects.get(user=request.user)
    
    # Fetch all children linked to the parent
    children = Child.objects.filter(parent=parent)
    
    # Fetch recent tasks and redemptions for each child
    for child in children:
        child.recent_tasks = Task.objects.filter(completed_by_children=child).order_by('-id')[:5]
        child.recent_redemptions = []  # Add logic for redemptions if applicable
    
    # Prepare summary statistics
    total_points = sum(child.points for child in children)
    total_children = children.count()
    
    # Prepare data for charts
    points_distribution = [child.points for child in children]
    task_completion = [child.completed_tasks.count() for child in children]
    
    context = {
        'parent': parent,
        'children': children,
        'total_points': total_points,
        'total_children': total_children,
        'points_distribution': points_distribution,
        'task_completion': task_completion,
    }
    
    return render(request, 'parent_stats.html', context)

@login_required
def child_detail(request, child_id):
    # Fetch the child object
    child = get_object_or_404(Child, id=child_id)
    
    # Fetch recent tasks and redemptions for the child
    recent_tasks = child.completed_tasks.all().order_by('-id')[:10]
    recent_redemptions = []  # Add logic for redemptions if applicable
    
    context = {
        'child': child,
        'recent_tasks': recent_tasks,
        'recent_redemptions': recent_redemptions,
    }
    return render(request, 'child_detail.html', context)
    
    
@login_required
def task_dashboard(request, child_id):
    # Fetch the child object
    child = get_object_or_404(Child, id=child_id)
    
    # Fetch all tasks for the child
    all_tasks = Task.objects.filter(completed_by_children=child).order_by('-completed_date')
    
    # Filter options (e.g., by status, date, etc.)
    status_filter = request.GET.get('status', 'all')  # 'all', 'completed', 'pending'
    date_filter = request.GET.get('date', 'all')      # 'all', 'today', 'this_week', 'this_month'

    # Apply filters
    if status_filter == 'completed':
        all_tasks = all_tasks.filter(completed_by_children=child)
    elif status_filter == 'pending':
        all_tasks = all_tasks.exclude(completed_by_children=child)

    if date_filter == 'today':
        all_tasks = all_tasks.filter(completed_date__date=timezone.now().date())
    elif date_filter == 'this_week':
        start_of_week = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
        all_tasks = all_tasks.filter(completed_date__date__gte=start_of_week)
    elif date_filter == 'this_month':
        all_tasks = all_tasks.filter(completed_date__month=timezone.now().month)

    context = {
        'child': child,
        'all_tasks': all_tasks,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'task_dashboard.html', context)
