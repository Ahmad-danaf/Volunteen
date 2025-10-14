from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from django.db.models import Prefetch
from django.http import JsonResponse, HttpResponseBadRequest
from mentorApp.models import Mentor,MentorGroup
from teenApp.entities import Task, TimeWindowRule, TaskRecurrence, Frequency
from mentorApp.forms import TaskForm,MentorGroupForm, validate_timewindow_payload
from teenApp.interface_adapters.forms import DateRangeForm
from teenApp.utils.NotificationManager import NotificationManager
from django.utils import timezone
import json
from datetime import datetime, time
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, F, IntegerField, Value, ExpressionWrapper, Subquery, OuterRef
from datetime import timedelta
from django.db import transaction
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils
from mentorApp.utils.MentorUtils import MentorUtils
from mentorApp.utils.MentorGroupUtils import MentorGroupUtils
from django.core.paginator import Paginator
from Volunteen.constants import TEEN_COINS_EXPIRATION_MONTHS
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_POST
import os, mimetypes
from uuid import uuid4
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django_q.tasks import async_task
from django.db.models.fields.files import FieldFile
import random
from django.core.files.uploadedfile import InMemoryUploadedFile
from childApp.utils.TeenCoinManager import TeenCoinManager

MOTIVATION_LINES = [
    "כל משימה שאתם נותנים – היא צעד לעתיד טוב יותר.",
    "אתם לא רק מלווים – אתם מעצבים חיים.",
    "ההשפעה שלכם ניכרת בכל נער ונערה שאתם מדריכים.",
    "המילים והמעשים שלכם נותנים השראה אמיתית.",
    "מאחורי כל הצלחה – יש ליווי תומך ואכפתי.",
    "כל משימה היא הזדמנות לצמיחה – למדריכים ולמתנדבים כאחד.",
    "הזמן שאתם משקיעים שווה זהב עבור הדור הצעיר.",
    "אתם מדליקים אור קטן שעושה הבדל גדול.",
    "אתם הופכים התנדבות לחוויה משמעותית באמת.",
    "המתנדבים זוכים – בזכות ההכוונה שלכם.",
    "בזכותכם Volunteen ממשיכה לגדול ולהשפיע.",
    "כל משימה ב־Volunteen מקרבת אתכם לשינוי אמיתי.",
    "אתם הלב הפועם של קהילת Volunteen.",
    "ב־Volunteen, כל ליווי שלכם הופך לרגע בלתי נשכח עבור הילדים.",
    "ביחד עם Volunteen – יוצרים עתיד של נתינה וצמיחה.",
    "הילדים ב־Volunteen סומכים עליכם – ואתם לא מאכזבים.",
    "החיבור בין ליווי אישי ל־Volunteen יוצר קסם אמיתי.",
    "בכל לחיצה על 'שמור משימה' – אתם משנים עולם קטן של מישהו.",
    "ההשפעה שלכם ב־Volunteen חזקה יותר ממה שאתם מדמיינים.",
    "ב־Volunteen, אתם לא רק מלווים – אתם מודל לחיקוי."
]
@login_required
def mentor_home(request):
    motivation_line = random.choice(MOTIVATION_LINES)
    mentor = get_object_or_404(Mentor, user=request.user)
    context = {
        'mentor_user_name': mentor,
        'available_teencoins': mentor.available_teencoins,
        'motivation_line': motivation_line,
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


def build_label(mentor_id, title, deadline, child_ids):
    deadline_str = deadline.isoformat() if deadline else "none"
    child_sig = "-".join(map(str, sorted(child_ids)))[:40]
    return f"create_task_{mentor_id}_{title.strip()}_{deadline_str}_{child_sig}"


@login_required
def add_task(request, task_id=None, duplicate=False, template=False):
    DEFAULT_IMG = "defaults/no-image.png"
    mentor = get_object_or_404(Mentor, user=request.user)
    task_data = {}
    mentor_groups = MentorGroupUtils.get_groups_for_mentor(mentor, active_only=True)

    # preset for duplication 
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
                "proof_requirement": original_task.proof_requirement,
            }
        tw_initial = []
        for r in original_task.time_window_rules.all():
            tw_initial.append({
                "window_type":   r.window_type,                                
                "specific_date": r.specific_date.isoformat() if r.specific_date else None,
                "weekday":       r.weekday,                                    
                "start_time":    r.start_time.strftime("%H:%M"),
                "end_time":      r.end_time.strftime("%H:%M"),
            })  
    else:
        tw_initial = []

    if request.method == "POST":
        form = TaskForm(
            mentor=mentor,
            data=request.POST,
            files=request.FILES,
            is_duplicate=duplicate,
            is_template=template,
        )
        if not form.is_valid():
            return render(request, "mentor_add_task.html", {
                "form": form,
                "timewindow_set": None,           
                "children": mentor.children.all(),
                "is_duplicate": duplicate,
                "available_teencoins": mentor.available_teencoins,
                "mentor_groups": mentor_groups,
                "initial_timewindows": json.dumps(tw_initial, ensure_ascii=False),

            })
        else:
            task_data.update(form.cleaned_data)

            assigned_children = task_data.pop("assigned_children", [])
            children_ids = list(assigned_children.values_list("id", flat=True))

            # handle image upload
            uploaded_img = task_data.get("img")

            try:
                # existing logic 
                if duplicate and isinstance(uploaded_img, FieldFile):
                    task_data["img"] = uploaded_img.name

                elif duplicate and (
                        uploaded_img in [None, "", DEFAULT_IMG]
                        or (isinstance(uploaded_img, str) and uploaded_img.endswith("no-image.png"))
                ):
                    task_data["img"] = original_task.img.name

                elif isinstance(uploaded_img, InMemoryUploadedFile):
                    ext = os.path.splitext(uploaded_img.name)[1] or mimetypes.guess_extension(
                        uploaded_img.content_type
                    )
                    filename = default_storage.save(
                        f"tasks/{uuid4().hex}{ext or ''}",
                        ContentFile(uploaded_img.read()),
                    )
                    task_data["img"] = filename

                # Make absolutely sure task_data["img"] is plain str or None
                if isinstance(task_data.get("img"), FieldFile):
                    task_data["img"] = task_data["img"].name
                img_val = task_data.get("img")
                if not (img_val is None or isinstance(img_val, str)):
                    task_data["img"] = getattr(img_val, "name", DEFAULT_IMG)
            except Exception as exc:
                print(f"Error saving image: {exc}")
                task_data["img"] = DEFAULT_IMG
                
            raw_payload = request.POST.get("timewindow_payload", "[]")
            try:
                timewindow_data = json.loads(raw_payload)
            except ValueError:
                messages.error(request, "פורמט חלונות הזמן אינו תקין")
                return redirect("mentorApp:mentor_add_task")

            try:
                timewindow_data = validate_timewindow_payload(timewindow_data)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect("mentorApp:mentor_add_task")

            # queue label with deadline + child sig
            label = build_label(
                mentor.id,
                task_data.get("title", ""),
                task_data.get("deadline"),
                children_ids,
            )
            if task_data.get("points", 0) <= 0:
                messages.error(request, "הנקודות למשימה צריכות להיות ערך חיובי")
                return redirect("mentorApp:mentor_add_task")
            task_cost = task_data.get("points", 0) * len(children_ids)
            mentor.refresh_from_db()
            if mentor.available_teencoins < task_cost:
                messages.error(request, "אין מספיק נקודות להקצאת המשימה")
                return redirect("mentorApp:mentor_add_task")
            async_task(
                "mentorApp.utils.MentorTaskUtils.MentorTaskUtils.create_task_with_assignments_async",
                mentor.id,
                children_ids,
                task_data,
                timewindow_data,
                q_options={"label": label, "queue_limit": 1},
            )

            messages.success(request, "המשימה נשלחת ברקע. תופיע בדף המשימות בעוד רגע 🙂")
            return redirect("mentorApp:mentor_home")
    else:
        form = TaskForm(
            mentor=mentor,
            initial=task_data,
            is_duplicate=duplicate,
            is_template=template,
        )     
    return render(
        request,
        "mentor_add_task.html",
        {
            "form": form,
            "children": mentor.children.all(),
            "is_duplicate": duplicate,
            "available_teencoins": mentor.available_teencoins,
            "mentor_groups": mentor_groups,
            "initial_timewindows": json.dumps(tw_initial, ensure_ascii=False),

        },
    )

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    mentor = get_object_or_404(Mentor, user=request.user)
    tw_initial = [
        {
            "window_type":   r.window_type,
            "specific_date": r.specific_date.isoformat() if r.specific_date else None,
            "weekday":       r.weekday,
            "start_time":    r.start_time.strftime("%H:%M"),
            "end_time":      r.end_time.strftime("%H:%M"),
        }
        for r in task.time_window_rules.all()
    ]
    
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, mentor=mentor)
        raw_payload = request.POST.get("timewindow_payload", "[]")
        try:
            timewindow_data = validate_timewindow_payload(json.loads(raw_payload))
        except Exception as e:
            messages.error(request, f"בעיה בחלונות הזמן: {e}")
            return redirect("mentorApp:edit_task", task_id=task.id)
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
            
            if updated_task.deadline >= timezone.localdate():
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
            task.time_window_rules.all().delete()               
            TimeWindowRule.objects.bulk_create(
                TimeWindowRule(task=updated_task, **tw) for tw in timewindow_data
            )

            mentor.save()
            messages.success(
                request,
                f"Task updated successfully! Remaining Teencoins: {mentor.available_teencoins}"
            )
            return redirect('mentorApp:mentor_home')

    else:
        form = TaskForm(instance=task, mentor=mentor)

    return render(request, 'edit_task.html', {
        'form': form,
        'task': task,
        'available_teencoins': mentor.available_teencoins,
        "initial_timewindows": json.dumps(tw_initial, ensure_ascii=False),
    })


@login_required
def mentor_task_list(request):
    mentor = Mentor.objects.get(user=request.user)
    current_date = timezone.now().date()
    mentor = get_object_or_404(Mentor, user=request.user)
    form = DateRangeForm(request.GET or None)
    tasks = Task.objects.filter(assigned_mentors=mentor, 
        deadline__gte=current_date).prefetch_related("time_window_rules")

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
            completed_task.awarded_coins = task.points
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
    Displays task completions assigned to the mentor within the last 3 days,
    grouped into two categories:
    1. On-Time (check-in/out within time window or no rule)
    2. Late (either check-in or check-out was late)
    """
    mentor = get_object_or_404(Mentor, user=request.user)
    three_days_ago = timezone.now() - timedelta(days=3)

    completions = TaskCompletion.objects.filter(
        task__assigned_mentors=mentor,
        status__in=['pending', 'checked_in', 'checked_out'],
        completion_date__gte=three_days_ago
    ).select_related('child__user', 'task')

    # Grouped data for frontend
    on_time = []
    late = []

    for comp in completions:
        is_late_checkin = comp.is_late_checkin
        is_late_checkout = comp.is_late_checkout

        entry = {
            "instance": comp,
            "late_checkin": is_late_checkin,
            "late_checkout": is_late_checkout,
        }

        if is_late_checkin or is_late_checkout:
            late.append(entry)
        else:
            on_time.append(entry)

    context = {
        "on_time_completions": on_time,
        "late_completions": late,
    }

    return render(request, "mentor_task_images.html", context)

@login_required
def review_task(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_ids = data.get('task_ids', [])
            action = data.get('action')
            awarded_coins_input = data.get('awarded_coins')  # optional for partial approval
            feedback = data.get('mentor_feedback', None)

            if not task_ids:
                return JsonResponse({'success': False, 'error': 'לא נבחרו משימות.'})

            processed_tasks = 0

            for task_id in task_ids:
                task_completion = get_object_or_404(TaskCompletion, id=task_id)

                if task_completion.status in ['approved', 'rejected']:
                    continue

                if action == 'approve':
                    task_completion.status = 'approved'

                    base_points = task_completion.task.points
                    bonus_points = task_completion.bonus_points or 0

                    if awarded_coins_input is not None:
                        # Partial approval flow
                        try:
                            awarded_input = int(awarded_coins_input)
                        except ValueError:
                            return JsonResponse({'success': False, 'error': 'מספר נקודות לא תקין.'})

                        # Ensure original points don't exceed task limit
                        original_points = min(base_points, awarded_input)
                    else:
                        # Full approval flow
                        original_points = base_points

                    # Total coins awarded = original points + bonus
                    total_awarded = original_points + bonus_points

                    task_completion.awarded_coins = total_awarded
                    task_completion.remaining_coins = total_awarded

                    # Award coins to child
                    task_completion.child.add_points(total_awarded)

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
    paginator = Paginator(template_tasks, 7)
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