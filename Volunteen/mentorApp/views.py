from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from django.db.models import Prefetch
from django.http import JsonResponse
from teenApp.entities.task import Task
from mentorApp.models import Mentor
from teenApp.use_cases.assign_bonus_points import AssignBonusPoints
from teenApp.interface_adapters.repositories import ChildRepository, TaskRepository, MentorRepository
from mentorApp.forms import  TaskImageForm, BonusPointsForm,TaskForm
from teenApp.interface_adapters.forms import DateRangeForm
from teenApp.utils import NotificationManager
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum,IntegerField, F
from datetime import timedelta

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
    efficiency_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0

    children = []
    for child in mentor.children.all():
        completed = TaskCompletion.objects.filter(child=child, task__in=tasks).count()
        assigned_tasks_by_mentor = tasks.filter(assigned_children=child).count()
        efficiency = round((completed / assigned_tasks_by_mentor) * 100, 2) if assigned_tasks_by_mentor > 0 else 0
        efficiency = int(efficiency) if efficiency == int(efficiency) else efficiency
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

    # Calculate total points from tasks and bonuses for each child
    for child in children:
        # Sum points from completed tasks and bonus points
        task_points = TaskCompletion.objects.filter(child=child).aggregate(
            total_task_points=Sum(F('task__points') + F('bonus_points'), output_field=IntegerField())
        )
        child.task_total_points = task_points['total_task_points'] or 0  # Fallback to 0 if no points

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
                return redirect('mentorApp:mentor_home')
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
def add_task(request, task_id=None, duplicate=False):
    mentor = get_object_or_404(Mentor, user=request.user)
    task = None

    if task_id: # for duplicating
        original_task = get_object_or_404(Task, id=task_id)
        print("1")
        print(original_task)
        if duplicate:
            # Create a new task with the same values, but DO NOT save yet
            task = Task(
                title=f"{original_task.title} (העתק)",
                description=original_task.description,
                points=original_task.points,
                deadline=original_task.deadline,
                additional_details=original_task.additional_details,
                img=original_task.img,  # Copy the image if needed
            )

    if request.method == 'POST':
        taskForm = TaskForm(mentor=mentor, data=request.POST, instance=task if not duplicate else None)
        if taskForm.is_valid():
            new_task = taskForm.save(commit=False)
            new_task.save()
            new_task.assigned_mentors.add(mentor)  # Add current mentor to assigned_mentors
            taskForm.save_m2m()
            return redirect('mentorApp:mentor_home')
    else:
        taskForm = TaskForm(mentor=mentor, instance=task)

    return render(request, 'mentor_add_task.html', {
        'form': taskForm,
        'children': mentor.children.all(),
        'task': task,
        'is_duplicate': duplicate,  # Pass duplication flag for UI updates
        'available_teencoins': mentor.available_teencoins
    })

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    mentor = get_object_or_404(Mentor, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, mentor=mentor)
        if form.is_valid():
            form.save()
            return redirect('mentorApp:mentor_task_list') 
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

    children = mentor.children.exclude(id__in=task.assigned_children.values_list('id', flat=True))

    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        selected_children_ids = [int(child_id) for child_id in selected_children_ids]  # לוודא שהערכים הם `int`
        
        for child_id in selected_children_ids:
            try:
                child = get_object_or_404(Child, id=child_id)

                task.assigned_children.add(child)

                TaskAssignment.objects.create(task=task, child=child, is_new=True)

                if child.user.email:
                    NotificationManager.sent_mail(
                        f'Dear {child.user.first_name}, a new task "{task.title}" has been assigned to you. Please check and complete it by {task.deadline}.',
                        child.user.email
                    )

                if child.user.phone:
                    phone_str = str(child.user.phone)
                    msg = (
                            f"🚀💡 *היי {child.user.username}, יש לך משימה חדשה שמחכה לך!* 💡🚀\n\n"
                            f"🔥 *המנטור שלך {mentor.user.first_name} הכין לך אתגר מיוחד!* 🔥\n"
                            f"💥 זאת ההזדמנות שלך להרוויח *{task.points} טינקאוינס!* 💰🏆\n\n"
                            f"📌 *משימה:* {task.title}\n"
                            f"🕒 *דדליין:* {task.deadline}\n\n"
                            f"⚡ *אל תפספס! כל משימה מקרבת אותך לפרסים שווים!* 🎁✨\n"
                            f"📲 *היכנס עכשיו והתחל לבצע!* >>> https://www.volunteen.site/"
                        )

                    NotificationManager.sent_whatsapp(msg, phone_str)

            except Child.DoesNotExist:
                print(f"Child with ID {child_id} does not exist.")

        task.assigned_mentors.add(mentor)

        messages.success(request, f"Task '{task.title}' successfully assigned to selected children.")
        return redirect('mentorApp:mentor_task_list')

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
        return redirect('mentorApp:points_assigned_success', task_id=task.id)

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

def send_whatsapp_message(request):
    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        message_text = request.POST.get('message_text')
        
        for child_id in selected_children_ids:
            #get child
            child=Child.objects.get(id=child_id)
            if child.user.phone:
                NotificationManager.sent_whatsapp(
                    message_text,
                    child.user.phone
                )
        return redirect('mentorApp:mentor_children_details')
    
    # Get all children
    children = Child.objects.all()
    return render(request, 'send_whatsapp_message.html', {'children': children})

@login_required
def mentor_task_images(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    seven_days_ago = timezone.now() - timedelta(days=7)  

    task_completions = TaskCompletion.objects.filter(
        task__assigned_mentors=mentor,
        status='pending', 
        completion_date__gte=seven_days_ago 
    )
    return render(request, 'mentor_task_images.html', {'completions': task_completions})
@csrf_exempt
@login_required
def review_task(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_ids = data.get('task_ids', [])
            action = data.get('action')

            if not task_ids:
                return JsonResponse({'success': False, 'error': 'לא נבחרו משימות.'})

            processed_tasks = 0
            for task_id in task_ids:
                task_completion = get_object_or_404(TaskCompletion, id=task_id)
                
                if task_completion.status != 'pending':
                    continue
                
                if action == 'approve':
                    task_completion.status = 'approved'
                    task_completion.task.approve_task(task_completion.child)
                elif action == 'reject':
                    task_completion.status = 'rejected'
                
                task_completion.save()
                processed_tasks += 1

            return JsonResponse({
                'success': True,
                'message': f"בוצע {processed_tasks} משימות בהצלחה.",
                'processed': processed_tasks
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'בקשה לא חוקית.'})