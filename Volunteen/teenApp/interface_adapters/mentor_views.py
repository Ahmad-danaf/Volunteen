from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.child import Child
from .forms import TaskForm 
from django.db.models import Prefetch
from django.http import JsonResponse
from teenApp.entities.task import Task
from teenApp.entities.mentor import Mentor
from teenApp.use_cases.assign_bonus_points import AssignBonusPoints
from teenApp.interface_adapters.repositories import ChildRepository, TaskRepository, MentorRepository
from .forms import  TaskImageForm, BonusPointsForm
from teenApp.utils import NotificationManager
from teenApp.interface_adapters.forms import DateRangeForm
from django.utils import timezone

@login_required
def mentor_home(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    tasks = Task.objects.filter(assigned_mentors=mentor)

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
        completed = TaskCompletion.objects.filter(child=child, task__in=tasks).count()
        assigned_tasks_by_mentor = tasks.filter(assigned_children=child).count()
        efficiency = (completed / assigned_tasks_by_mentor) * 100 if assigned_tasks_by_mentor > 0 else 0
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
        'tasks': tasks,
    }
    return render(request, 'mentor_home.html', context)

@login_required
def mentor_children_details(request):
    mentor = get_object_or_404(Mentor, user=request.user)

    # Prefetch task completions for each child to avoid N+1 queries
    children = mentor.children.prefetch_related(
        Prefetch('taskcompletion_set', queryset=TaskCompletion.objects.select_related('task').order_by('-completion_date'))
    ).order_by('-points')

    return render(request, 'mentor_children_details.html', {'children': children})



@login_required
def mentor_completed_tasks_view(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    form = DateRangeForm(request.GET or None)
    task_data = []

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = None
        end_date = None

    tasks = Task.objects.filter(assigned_mentors=mentor, completed=True)
    if start_date and end_date:
        tasks = tasks.filter(deadline__range=(start_date, end_date))

        for task in tasks:
            completions = TaskCompletion.objects.filter(task=task)
            task_info = {
                'task': task,
                'form': TaskImageForm(instance=task),
                'completed_by': [completion.child for completion in completions],
                'completed_count': completions.count(),
            }
            task_data.append(task_info)

    return render(request, 'mentor_completed_tasks_view.html', {'task_data': task_data, 'form': form})


assign_bonus_points = AssignBonusPoints(
    child_repository=ChildRepository(),
    task_repository=TaskRepository(),
    mentor_repository=MentorRepository()
)

@login_required
def assign_bonus(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    
    if request.method == 'POST':
        form = BonusPointsForm(mentor, request.POST)
        if form.is_valid():
            task = form.cleaned_data['task']
            child = form.cleaned_data['child']
            bonus_points = form.cleaned_data['bonus_points']
            
            if bonus_points > 10:
                return render(request, 'assign_bonus.html', {'form': form, 'error': 'Maximum of 10 bonus points per assignment is allowed.'})
            
            try:
                assign_bonus_points.execute(task.id, child.id, mentor.id, bonus_points)
                TaskCompletion.objects.filter(task=task, child=child).update(bonus_points=bonus_points)
                return redirect('mentor_home')
            except ValueError as e:
                return render(request, 'assign_bonus.html', {'form': form, 'error': str(e)})
    else:
        form = BonusPointsForm(mentor)
    
    return render(request, 'assign_bonus.html', {'form': form})

def load_children(request):
    task_id = request.GET.get('task_id')
    
    # Filter children based on TaskCompletion for the given task
    completed_children = Child.objects.filter(
        taskcompletion__task_id=task_id  # Join with TaskCompletion model to get children who have completed the task
    ).order_by('user__username')

    # Return the list of children with their IDs and usernames
    return JsonResponse(list(completed_children.values('id', 'user__username')), safe=False)

@login_required
def add_task(request):
    mentor = get_object_or_404(Mentor, user=request.user)

    if request.method == 'POST':
        form = TaskForm(mentor=mentor, data=request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.mentor = mentor
            task.save()
            form.save_m2m()  # Save the many-to-many data for the form
            return redirect('mentor_home')
    else:
        form = TaskForm(mentor=mentor)

    return render(request, 'add_task.html', {'form': form})

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    mentor = get_object_or_404(Mentor, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, mentor=mentor)
        if form.is_valid():
            form.save()
            return redirect('mentor_task_list')  # Redirect to mentor task list or another appropriate page
    else:
        form = TaskForm(instance=task, mentor=mentor)
    return render(request, 'edit_task.html', {'form': form, 'task': task})

@login_required
def mentor_active_list(request):
    mentor = Mentor.objects.get(user=request.user)
    tasks = Task.objects.filter(assigned_mentors=mentor)
    return render(request, 'list_tasks.html', {'tasks': tasks})

@login_required
def mentor_task_list(request):
    current_date = timezone.now().date()
    mentor = get_object_or_404(Mentor, user=request.user)
    form = DateRangeForm(request.GET or None)
    tasks = Task.objects.filter(assigned_mentors=mentor, deadline__gte=current_date)

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        tasks = tasks.filter(deadline__range=(start_date, end_date))

    return render(request, 'mentor_task_list.html', {'tasks': tasks, 'form': form})

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
            if child.user.email:
                NotificationManager.sent_mail(
                    f'Dear {child.user.first_name}, a new task "{task.title}" has been assigned to you. Please check and complete it by {task.deadline}.',
                    child.user.email
                )
        task.assigned_mentors.add(mentor)
        messages.success(request, f"Task '{task.title}' successfully assigned to selected children.")
        return redirect('mentor_task_list')

    return render(request, 'assign_task.html', {'task': task, 'children': children})

@login_required
def assign_points(request, task_id):
    mentor = Mentor.objects.get(user=request.user)
    task = get_object_or_404(Task, id=task_id)
    
    # Get all assigned children
    children = mentor.children.filter(id__in=task.assigned_children.values_list('id', flat=True))

    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        for child_id in selected_children_ids:
            child = get_object_or_404(Child, id=child_id)
            task.mark_completed(child)
        messages.success(request, f"Points successfully assigned for task '{task.title}' to selected children.")
        return redirect('points_assigned_success', task_id=task.id)

    # Prepare data for children with completion status
    children_with_status = []
    for child in children:
        completed = TaskCompletion.objects.filter(task=task, child=child).exists()
        children_with_status.append({'child': child, 'completed': completed})

    return render(request, 'assign_points.html', {'task': task, 'children_with_status': children_with_status})


@login_required
def points_assigned_success(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    completed_children = Child.objects.filter(
        id__in=TaskCompletion.objects.filter(task=task).values_list('child_id', flat=True)
    ) 
    return render(request, 'points_assigned_success.html', {'task': task, 'children': completed_children})

