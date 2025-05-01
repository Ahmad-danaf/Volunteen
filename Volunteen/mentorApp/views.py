from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from django.db.models import Prefetch
from django.http import JsonResponse, HttpResponseBadRequest
from mentorApp.models import Mentor,MentorGroup
from teenApp.entities.task import Task
from mentorApp.forms import TaskForm,MentorGroupForm
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
from mentorApp.utils.MentorGroupUtils import MentorGroupUtils
from django.core.paginator import Paginator
from Volunteen.constants import TEEN_COINS_EXPIRATION_MONTHS
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_POST

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

    # Fetch only active mentor groups
    mentor_groups = MentorGroupUtils.get_groups_for_mentor(mentor, active_only=True)

    if task_id:
        original_task = get_object_or_404(Task, id=task_id)
        if duplicate:
            task_data = {
                "title": str(original_task.title),
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
                new_task = MentorTaskUtils.create_task_with_assignments(mentor, children_ids, task_data)
                if duplicate and original_task.img:
                    if taskForm.cleaned_data.get('img') == 'defaults/no-image.png':
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
        'available_teencoins': mentor.available_teencoins,
        'mentor_groups': mentor_groups,
    })

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    mentor = get_object_or_404(Mentor, user=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, mentor=mentor)
        if form.is_valid():
            updated_task = form.save(commit=False)

            old_points = task.points  
            new_points = form.cleaned_data['points']
            old_children = set(task.assigned_children.all())
            new_children = set(form.cleaned_data['assigned_children'])

            added_children = new_children - old_children
            removed_children = old_children - new_children

            old_cost = old_points * len(old_children)
            new_cost = new_points * len(new_children)
            cost_difference = new_cost - old_cost

            if mentor.available_teencoins < cost_difference:
                messages.error(request, "Not enough Teencoins to update this task.")
            else:
                updated_task.save()
                form.save_m2m()

                for child in added_children:
                    TaskAssignment.objects.create(
                        task=updated_task,
                        child=child,
                        assigned_by=mentor.user
                    )

                for child in removed_children:
                    completions = TaskCompletion.objects.filter(task=updated_task, child=child)
                    for completion in completions:
                        completion.delete()
                    TaskAssignment.objects.filter(task=updated_task,child=child).delete()


                mentor.available_teencoins -= cost_difference
                mentor.save()

                messages.success(
                    request,
                    f"Task updated successfully! Remaining Teencoins: {mentor.available_teencoins}"
                )
                return redirect('mentorApp:mentor_task_list')

    else:
        form = TaskForm(instance=task, mentor=mentor)

    return render(request, 'edit_task.html', {
        'form': form,
        'task': task,
        'available_teencoins': mentor.available_teencoins,
    })


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
            
        return redirect('mentorApp:mentor_children_details')
    
    # Get all children
    children = Child.objects.all()
    return render(request, 'send_whatsapp_message.html', {'children': children})

@login_required
def mentor_task_images(request):
    """
    Retrieves task completions assigned to the mentor that are in 'pending', 'checked_in', or 'checked_out' status
    within the last 3 days.
    """
    mentor = get_object_or_404(Mentor, user=request.user)
    three_days_ago = timezone.now() - timedelta(days=3)  

    task_completions = TaskCompletion.objects.filter(
        task__assigned_mentors=mentor,
        status__in=['pending', 'checked_in', 'checked_out'],  
        completion_date__gte=three_days_ago
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
            feedback = data.get('mentor_feedback', None)

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
                    task_completion.mentor_feedback = feedback
                
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
def bonus_task_selection(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    today = timezone.now().date()
    start_date = today - relativedelta(months=TEEN_COINS_EXPIRATION_MONTHS)
    end_date = today + relativedelta(months=TEEN_COINS_EXPIRATION_MONTHS)
    tasks = MentorTaskUtils.get_all_tasks_assigned_to_mentor(mentor, start_date, end_date).order_by('-deadline')
    return render(request, 'mentorApp/bonus/bonus_task_selection.html', {'tasks': tasks})


@login_required
def bonus_children_selection(request, task_id):
    mentor = get_object_or_404(Mentor, user=request.user)
    task = get_object_or_404(Task, id=task_id)
    
    approved_completions = MentorTaskUtils.get_approved_completions_for_task(mentor, task)
    for completion in approved_completions:
        completion.expiry_date = completion.completion_date + relativedelta(months=TEEN_COINS_EXPIRATION_MONTHS)
    
    context = {
        'task': task,
        'approved_completions': approved_completions,
        'available_teencoins': mentor.available_teencoins,
        'teencoins_expiration_months': TEEN_COINS_EXPIRATION_MONTHS,
    }
    return render(request, 'mentorApp/bonus/bonus_children_selection.html', context)


@login_required
def assign_bonus_multi(request, task_id):
    """
    Processes bonus assignments for multiple task completions.
    The mentor selects one or more completions and provides bonus points,
    which are then assigned to each selected task completion.
    """
    if request.method == 'POST':
        mentor = get_object_or_404(Mentor, user=request.user)
        task = get_object_or_404(Task, id=task_id)
        bonus_points = int(request.POST.get('bonus_points', '0'))
        completion_ids = request.POST.getlist('completion_ids')
        
        success_count = 0
        errors = []
        for tc_id in completion_ids:
            try:
                # This utility method applies the bonus to a single task completion
                updated_tc = MentorTaskUtils.assign_bonus_to_task_completion(mentor, tc_id, bonus_points)
                success_count += 1
            except ValueError as e:
                errors.append(str(e))
        
        if success_count > 0:
            messages.success(request, f"נוספו {bonus_points} נקודות בונוס ל-{success_count} השלמות עבור {task.title}!")
        if errors:
            messages.error(request, "Errors occurred: " + "; ".join(errors))
        return redirect('mentorApp:mentor_home')
    else:
        messages.error(request, "Unauthorized access. Bonus can only be assigned via POST.")
        return redirect('mentorApp:mentor_home')


@login_required
def mentor_group_list(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    groups = MentorGroup.objects.filter(mentor=mentor)
    return render(request, 'mentorApp/groups/group_list.html', {'groups': groups})


@login_required
def mentor_group_create(request):
    mentor = get_object_or_404(Mentor, user=request.user)
    if request.method == 'POST':
        form = MentorGroupForm(request.POST, mentor=mentor)
        if form.is_valid():
            group = form.save(commit=False)
            group.mentor = mentor
            group.save()
            form.save_m2m()
            return redirect('mentorApp:mentor_group_list')
    else:
        form = MentorGroupForm(mentor=mentor)
    return render(request, 'mentorApp/groups/group_form.html', {'form': form})



@login_required
def mentor_group_edit(request, group_id):
    mentor = get_object_or_404(Mentor, user=request.user)
    group = get_object_or_404(MentorGroup, id=group_id, mentor=mentor)

    if request.method == 'POST':
        form = MentorGroupForm(request.POST, instance=group, mentor=mentor)
        if form.is_valid():
            form.save()
            return redirect('mentorApp:mentor_group_list')
    else:
        form = MentorGroupForm(instance=group, mentor=mentor)
    return render(request, 'mentorApp/groups/group_form.html', {'form': form, 'group': group})


@login_required
@require_POST
def mentor_group_toggle_active(request, group_id):
    mentor = get_object_or_404(Mentor, user=request.user)
    group = get_object_or_404(MentorGroup, id=group_id, mentor=mentor)
    group.is_active = not group.is_active
    group.save()
    return redirect('mentorApp:mentor_group_list')

@login_required
@require_POST
def mentor_group_delete(request, group_id):
    mentor = get_object_or_404(Mentor, user=request.user)
    group = get_object_or_404(MentorGroup, id=group_id, mentor=mentor)
    
    group.delete()
    messages.success(request, 'הקבוצה נמחקה בהצלחה.')
    return redirect('mentorApp:mentor_group_list')