from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from django.db import transaction
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from teenApp.entities.task import TaskGroup, Task
from mentorApp.models import Mentor
from childApp.models import Child
import json


@login_required
def task_group_dashboard(request):
    """
    Main dashboard for TaskGroups - displays all groups for the current mentor
    """
    try:
        mentor = request.user.mentor
    except:
        messages.error(request, "אינך רשום כמנטור במערכת")
        return redirect('mentorApp:mentor_home')
    
    task_groups = TaskGroup.objects.filter(created_by=mentor).annotate(
        task_count=Count('tasks')
    ).order_by('-created_at')
    
    paginator = Paginator(task_groups, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'task_groups': page_obj,
        'mentor': mentor,
        'total_groups': task_groups.count(),
    }
    return render(request, 'mentorApp/task_groups/dashboard.html', context)


@login_required
def create_task_group(request):
    """
    Create a new TaskGroup
    """
    try:
        mentor = request.user.mentor
    except:
        messages.error(request, "אינך רשום כמנטור במערכת")
        return redirect('mentorApp:mentor_home')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name:
            messages.error(request, "שם הקבוצה הוא שדה חובה")
            return render(request, 'mentorApp/task_groups/create.html')
        
        if TaskGroup.objects.filter(created_by=mentor, name=name).exists():
            messages.error(request, "קבוצה עם שם זה כבר קיימת")
            return render(request, 'mentorApp/task_groups/create.html', {
                'name': name,
                'description': description
            })
        
        try:
            task_group = TaskGroup.objects.create(
                name=name,
                description=description,
                created_by=mentor
            )
            messages.success(request, f"קבוצת המשימות '{name}' נוצרה בהצלחה!")
            return redirect('mentorApp:template_list')
        except Exception as e:
            messages.error(request, "אירעה שגיאה ביצירת הקבוצה")
    
    return render(request, 'mentorApp/task_groups/create.html')


@login_required
def edit_task_group(request, group_id):
    """
    Edit an existing TaskGroup
    """
    try:
        mentor = request.user.mentor
    except:
        messages.error(request, "אינך רשום כמנטור במערכת")
        return redirect('mentorApp:mentor_home')
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        if not name:
            messages.error(request, "שם הקבוצה הוא שדה חובה")
            return render(request, 'mentorApp/task_groups/edit.html', {
                'task_group': task_group,
                'name': name,
                'description': description
            })
        
        if TaskGroup.objects.filter(created_by=mentor, name=name).exclude(id=group_id).exists():
            messages.error(request, "קבוצה עם שם זה כבר קיימת")
            return render(request, 'mentorApp/task_groups/edit.html', {
                'task_group': task_group,
                'name': name,
                'description': description
            })
        
        try:
            task_group.name = name
            task_group.description = description
            task_group.is_active = is_active
            task_group.save()
            messages.success(request, f"קבוצת המשימות '{name}' עודכנה בהצלחה!")
            return redirect('mentorApp:task_group_detail', group_id=task_group.id)
        except Exception as e:
            messages.error(request, "אירעה שגיאה בעדכון הקבוצה")
    
    return render(request, 'mentorApp/task_groups/edit.html', {'task_group': task_group})


@login_required
def delete_task_group(request, group_id):
    """
    Delete a TaskGroup
    """
    try:
        mentor = request.user.mentor
    except:
        messages.error(request, "אינך רשום כמנטור במערכת")
        return redirect('mentorApp:mentor_home')
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    
    if request.method == 'POST':
        group_name = task_group.name
        task_count = task_group.tasks.count()
        
        try:
            task_group.delete()
            messages.success(request, f"קבוצת המשימות '{group_name}' נמחקה בהצלחה (כולל {task_count} משימות)")
            return redirect('mentorApp:task_group_dashboard')
        except Exception as e:
            messages.error(request, "אירעה שגיאה במחיקת הקבוצה")
    
    context = {
        'task_group': task_group,
        'task_count': task_group.tasks.count()
    }
    return render(request, 'mentorApp/task_groups/delete_confirm.html', context)


@login_required
def task_group_detail(request, group_id):
    """
    View TaskGroup details including assigned children
    """
    try:
        mentor = request.user.mentor
    except:
        messages.error(request, "אינך רשום כמנטור במערכת")
        return redirect('mentorApp:mentor_home')
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    tasks_in_group = task_group.tasks.all()
    
    if tasks_in_group.exists():
        assigned_children_ids = set()
        for task in tasks_in_group:
            if not assigned_children_ids:
                assigned_children_ids = set(task.assigned_children.values_list('id', flat=True))
            else:
                current_task_children = set(task.assigned_children.values_list('id', flat=True))
                assigned_children_ids = assigned_children_ids.intersection(current_task_children)
        
        children_in_group = Child.objects.filter(
            id__in=assigned_children_ids
        ).select_related('user').order_by('user__date_joined')
    else:
        children_in_group = Child.objects.none()
    
    mentor_children = Child.objects.filter(
        mentors=mentor
    ).select_related('user').exclude(
        id__in=children_in_group.values_list('id', flat=True)
    ).order_by('user__date_joined')
    
    children_paginator = Paginator(children_in_group, 15)
    children_page_number = request.GET.get('children_page')
    children_page_obj = children_paginator.get_page(children_page_number)
    
    available_paginator = Paginator(mentor_children, 15)
    available_page_number = request.GET.get('available_page')
    available_page_obj = available_paginator.get_page(available_page_number)
    
    context = {
        'task_group': task_group,
        'tasks_in_group': tasks_in_group,
        'children_in_group': children_page_obj,
        'available_children': available_page_obj,
        'total_children_in_group': children_in_group.count(),
        'total_available_children': mentor_children.count(),
    }
    
    return render(request, 'mentorApp/task_groups/detail.html', context)


@login_required
@require_http_methods(["POST"])
def add_children_to_group(request, group_id):
    """
    Add selected children to all tasks in the TaskGroup
    """
    try:
        mentor = request.user.mentor
    except:
        return JsonResponse({'success': False, 'error': 'אינך רשום כמנטור במערכת'})
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    
    try:  
        data = json.loads(request.body)
        child_ids = data.get('child_ids', [])        
        if not child_ids:
            return JsonResponse({'success': False, 'error': 'לא נבחרו חניכים'})
        
        valid_children = Child.objects.filter(
            id__in=child_ids,
            mentors=mentor
        )   
        if len(child_ids) != valid_children.count():
            return JsonResponse({'success': False, 'error': 'חלק מהחניכים שנבחרו אינם שייכים לך'})
        
        tasks_in_group = task_group.tasks.all()
        if not tasks_in_group.exists():
            return JsonResponse({'success': False, 'error': 'אין משימות בקבוצה זו'})
        
        added_count = 0
        for task in tasks_in_group:
            for child in valid_children:
                if child not in task.assigned_children.all():
                    task.assigned_children.add(child)
                    added_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{valid_children.count()} חניכים נוספו לכל {tasks_in_group.count()} המשימות בקבוצה',
            'added_assignments': added_count
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return JsonResponse({'success': False, 'error': 'נתונים שגויים'})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return JsonResponse({'success': False, 'error': f'אירעה שגיאה במערכת: {str(e)}'})


@login_required
@require_http_methods(["POST"])
def remove_child_from_group(request, group_id, child_id):
    """
    Remove a child from all tasks in the TaskGroup
    """
    try:
        mentor = request.user.mentor
    except:
        return JsonResponse({'success': False, 'error': 'אינך רשום כמנטור במערכת'})
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    child = get_object_or_404(Child, id=child_id, mentors=mentor)
    
    try:
        tasks_in_group = task_group.tasks.all()
        removed_count = 0
        for task in tasks_in_group:
            if child in task.assigned_children.all():
                task.assigned_children.remove(child)
                removed_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{child.user.username} הוסר מ-{removed_count} משימות בקבוצה',
            'removed_count': removed_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'אירעה שגיאה במערכת'})


@login_required
def search_children_ajax(request, group_id):
    """
    AJAX endpoint for searching available children to add to group
    """
    try:
        mentor = request.user.mentor
    except:
        return JsonResponse({'success': False, 'error': 'אינך רשום כמנטור במערכת'})
    
    task_group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    search_query = request.GET.get('q', '').strip()
    
    tasks_in_group = task_group.tasks.all()
    children_in_group_ids = set()
    if tasks_in_group.exists():
        for task in tasks_in_group:
            if not children_in_group_ids:
                children_in_group_ids = set(task.assigned_children.values_list('id', flat=True))
            else:
                current_task_children = set(task.assigned_children.values_list('id', flat=True))
                children_in_group_ids = children_in_group_ids.intersection(current_task_children)
    
    available_children = Child.objects.filter(
        mentors=mentor
    ).exclude(
        id__in=children_in_group_ids
    ).select_related('user')
    
    if search_query:
        available_children = available_children.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(identifier__icontains=search_query)
        )
    
    available_children = available_children[:20]
    
    children_data = []
    for child in available_children:
        children_data.append({
            'id': child.id,
            'username': child.user.username,
            'full_name': f"{child.user.first_name} {child.user.last_name}".strip(),
            'identifier': child.identifier,
            'join_date': child.user.date_joined.strftime('%d/%m/%Y')
        })
    
    return JsonResponse({
        'success': True,
        'children': children_data,
        'total': len(children_data)
    })
    
    
@login_required
@require_POST
def add_task_to_group(request):
    mentor = request.user.mentor
    task_id = request.POST.get("task_id")
    group_id = request.POST.get("group_id")

    if not task_id or not group_id:
        return JsonResponse({"success": False, "error": "Missing task_id or group_id."}, status=400)

    group = get_object_or_404(TaskGroup, id=group_id, created_by=mentor)
    task = get_object_or_404(Task, id=task_id, assigned_mentors=mentor, is_template=True)
    with transaction.atomic():
        if group in task.groups.all():
            return JsonResponse({
                "success": False,
                "error": f"המשימה כבר משויכת לקבוצה '{group.name}'."
            }, status=400)
        task.groups.add(group)

    return JsonResponse({
        "success": True,
        "message": f"המשימה '{task.title}' נוספה בהצלחה לקבוצה '{group.name}'.",
        "task_id": task.id,
        "group_id": group.id,
    })