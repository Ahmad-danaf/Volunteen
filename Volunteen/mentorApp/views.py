from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from django.db.models import Prefetch
from django.http import JsonResponse
from mentorApp.models import Mentor
from teenApp.entities.task import Task
from mentorApp.forms import TaskForm
from teenApp.interface_adapters.forms import DateRangeForm
from teenApp.utils.NotificationManager import NotificationManager
from django.utils import timezone
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum,IntegerField, F
from datetime import timedelta
from django.db import transaction
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils
from mentorApp.utils.MentorUtils import MentorUtils
from django.core.paginator import Paginator
from Volunteen.constants import TEEN_COINS_EXPIRATION_MONTHS

@login_required
def mentor_home(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    context = {
        'mentor': mentor,
    }
    return render(request, 'mentor_home.html', context)

@login_required
def mentor_children_details(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    children = MentorTaskUtils.get_children_with_completed_tasks_for_mentor(mentor)
    return render(request, 'mentor_children_details.html', {'children': children})


@login_required
def children_performance(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    performance_data = MentorUtils.get_children_performance_data(mentor)
    context = {
        'mentor': mentor,
        'performance_data': performance_data,
    }
    return render(request, 'mentor_children_performance.html', context)





@login_required
def add_task(request, task_id=None, duplicate=False, template=False):
    mentor = get_object_or_404(Mentor, user=request.user)
    task_data = {}

    # Handle task duplication
    if task_id:
        original_task = get_object_or_404(Task, id=task_id)
        if duplicate:
            task_data = {
                "title": f"{original_task.title} (העתק)",
                "description": original_task.description,
                "points": original_task.points,
                "deadline": None,
                "additional_details": original_task.additional_details,
                "img": original_task.img,
            }

    if request.method == 'POST':
        taskForm = TaskForm(
            mentor=mentor,
            data=request.POST,
            files=request.FILES,
            is_duplicate=duplicate,
            is_template=template
        )

        if taskForm.is_valid():
            # Extract task fields and assigned children
            task_data.update(taskForm.cleaned_data)
            assigned_children = taskForm.cleaned_data.get('assigned_children', [])
            children_ids = list(assigned_children.values_list("id", flat=True))
            if duplicate and not taskForm.cleaned_data.get('img'):
                task_data['img'] = original_task.img
            try:
                # Create the task with mentor assignment and children
                new_task = MentorTaskUtils.create_task_with_assignments(mentor, children_ids, task_data)
                if duplicate and original_task.img:
                    if taskForm.cleaned_data.get('img')=='defaults/no-image.png':
                        new_task.img = original_task.img
                        new_task.save()


                messages.success(request, f"המשימה נוספה בהצלחה! יתרת Teencoins: {mentor.available_teencoins}")
                return redirect('mentorApp:mentor_home')

            except ValueError as e:
                messages.error(request, str(e))

    else:
        taskForm = TaskForm(
            mentor=mentor,
            initial=task_data,
            is_duplicate=duplicate,
            is_template=template
        )
    return render(request, 'mentor_add_task.html', {
        'form': taskForm,
        'children': mentor.children.all(),
        'is_duplicate': duplicate,
        'available_teencoins': mentor.available_teencoins
    })

@login_required
def edit_task(request, task_id):
     task = get_object_or_404(Task, id=task_id)
     mentor = get_object_or_404(Mentor, user=request.user)
     
     if request.method == 'POST':
         form = TaskForm(request.POST, request.FILES, instance=task, mentor=mentor)
         if form.is_valid():
             updated_task = form.save(commit=False)
             assigned_children = form.cleaned_data['assigned_children']
             total_cost = updated_task.points * assigned_children.count()
             
             # Calculate the Teencoins difference
             previous_assigned_count = task.assigned_children.count()
             previous_cost = task.points * previous_assigned_count
             new_cost = updated_task.points * assigned_children.count()
             cost_difference = new_cost - previous_cost
             
             if mentor.available_teencoins - cost_difference < 0:
                 messages.error(request, "Not enough Teencoins to update this task.")
             else:
                 updated_task.save()
                 form.save_m2m()
                 
                 # Update Teencoins
                 mentor.available_teencoins -= cost_difference
                 mentor.save()
                 
                 messages.success(request, f"Task updated successfully! Remaining Teencoins: {mentor.available_teencoins}")
                 return redirect('mentorApp:mentor_task_list') 
     else:
         form = TaskForm(instance=task, mentor=mentor)
     
     return render(request, 'edit_task.html', {'form': form, 'task': task, 'available_teencoins': mentor.available_teencoins})


@login_required
def mentor_task_list(request):
    mentor = Mentor.objects.get(user=request.user)
    current_date = timezone.now().date()
    mentor = get_object_or_404(Mentor, user=request.user)
    form = DateRangeForm(request.GET or None)
    tasks = Task.objects.filter(assigned_mentors=mentor, deadline__gte=current_date)

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        tasks = tasks.filter(deadline__range=(start_date, end_date))

    return render(request, 'mentor_task_list.html', {'tasks': tasks, 'form': form, 'available_teencoins': mentor.available_teencoins})

@login_required
def assign_task(request, task_id):
    mentor = Mentor.objects.get(user=request.user)
    task = get_object_or_404(Task, id=task_id)

    children = mentor.children.exclude(id__in=task.assigned_children.values_list('id', flat=True))

    if request.method == 'POST':
        selected_children_ids = request.POST.getlist('children')
        selected_children_ids = [int(child_id) for child_id in selected_children_ids]

        total_cost = task.points * len(selected_children_ids)
        
        if mentor.available_teencoins < total_cost:
            messages.error(request, "Not enough Teencoins to assign this task.")
            return render(request, 'assign_task.html', {'task': task, 'children': children, 'show_popup': True})
        else:
            for child_id in selected_children_ids:
                try:
                    child = get_object_or_404(Child, id=child_id)
                    task.assigned_children.add(child)
                    TaskAssignment.objects.get_or_create(task=task, child=child, is_new=True, assigned_by=mentor.user)

                    

                except Child.DoesNotExist:
                    print(f"Child with ID {child_id} does not exist.")

            task.assigned_mentors.add(mentor)
            
            # Deduct Teencoins
            mentor.available_teencoins -= total_cost
            mentor.save()

            messages.success(request, f"Task '{task.title}' successfully assigned to selected children. Remaining Teencoins: {mentor.available_teencoins}")
            return redirect('mentorApp:mentor_task_list')

    return render(request, 'assign_task.html', {'task': task, 'children': children, 'available_teencoins': mentor.available_teencoins})



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
            
            completed_task = TaskCompletion.objects.get(task=task, child=child)
            completed_task.remaining_coins = completed_task.bonus_points + task.points
            completed_task.save()
        messages.success(request, f"Points successfully assigned for task '{task.title}' to selected children.")
        return redirect('mentorApp:points_assigned_success', task_id=task.id)

    # Prepare data for children with completion status
    children_with_status = []
    for child in children:
        completed = TaskCompletion.objects.filter(task=task, child=child, status='approved').exists()
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
    """
    Retrieves task completions assigned to the mentor that are in 'pending', 'checked_in', or 'checked_out' status
    within the last 7 days.
    """
    mentor = get_object_or_404(Mentor, user=request.user)
    seven_days_ago = timezone.now() - timedelta(days=7)  

    task_completions = TaskCompletion.objects.filter(
        task__assigned_mentors=mentor,
        status__in=['pending', 'checked_in', 'checked_out'],  
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
                
                if task_completion.status =='approved' or task_completion.status == 'rejected':
                    continue
                
                if action == 'approve':
                    task_completion.status = 'approved'
                    task_completion.task.approve_task(task_completion.child)
                    task_completion.remaining_coins = task_completion.task.points+task_completion.bonus_points
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



@login_required
def template_list(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    search_query = request.GET.get('search', '')
    template_tasks = MentorTaskUtils.get_template_tasks(mentor, search_query)
    
    # Paginate the results (5 per page as an example)
    paginator = Paginator(template_tasks, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'mentor_template_list.html', context)
    
    
@login_required
def remove_from_templates(request, task_id):
    mentor = get_object_or_404(Mentor, user=request.user)
    task = get_object_or_404(Task, id=task_id, is_template=True, assigned_mentors=mentor)
    
    task.is_template = False
    task.save()
    messages.success(request, f"'{task.title}' was removed from templates.")
    return redirect('mentorApp:template_list')


@login_required
def bonus_child_selection(request):
    """
    Page for mentor to select a child to whom they want to give a bonus.
    Provides a search box for filtering children by username or name.
    """
    mentor = get_object_or_404(Mentor, user=request.user)
    search_query = request.GET.get('search', '')

    children = MentorUtils.get_children_for_mentor(mentor, search_query)

    context = {
        'children': children,
        'search_query': search_query
    }
    return render(request, 'bonus_child_selection.html', context)


@login_required
def child_bonus_detail(request, child_id):
    """
    Lists the completed tasks for this child that are assigned to the current mentor
    and have not expired. Mentor can give bonuses here.
    """
    mentor = get_object_or_404(Mentor, user=request.user)
    child = get_object_or_404(Child, id=child_id)

    active_completions = MentorTaskUtils.get_active_completions_for_mentor_child(mentor, child)

    context = {
        'child': child,
        'active_completions': active_completions,
        'available_teencoins': mentor.available_teencoins,
        'teencoins_expiration_months': TEEN_COINS_EXPIRATION_MONTHS
    }
    return render(request, 'child_bonus_detail.html', context)


@login_required
def assign_bonus(request, task_completion_id):
    """
    POST-only view that awards a bonus to a specific TaskCompletion.
    The bonus points come from the 'bonus_points' field in the form.
    If the mentor doesn't have enough coins, we show an error.
    """
    if request.method == 'POST':
        mentor = get_object_or_404(Mentor, user=request.user)
        bonus_points = int(request.POST.get('bonus_points', '0'))

        try:
            updated_tc = MentorTaskUtils.assign_bonus_to_task_completion(mentor, task_completion_id, bonus_points)
            messages.success(request, f"נוספו {bonus_points} נקודות בונוס עבור {updated_tc.task.title}!")
        except ValueError as e:
            messages.error(request, str(e))

        # Redirect back to the detail page for the child's completions
        return redirect('mentorApp:child_bonus_detail', child_id=updated_tc.child.id)
    else:
        messages.error(request, "גישה לא מורשית. ניתן לשלוח בונוס רק באמצעות POST.")
        return redirect('mentorApp:bonus_child_selection')