from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.core.files import File
import os
from django.core.files.base import ContentFile
from django.shortcuts import render,redirect,get_object_or_404
from shopApp.models import Campaign, Shop
from managementApp.forms.campaign_forms import CampaignStep1Form,CampaignTaskForm
from django.forms import modelformset_factory
from teenApp.entities.task import Task
from managementApp.utils.CampaignManagerUtils import CampaignManagerUtils
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.utils.CampaignUtils import CampaignUtils
from childApp.models import Child
from django.views.decorators.http import require_POST
from managementApp.decorators import campaign_manager_required
from datetime import date, datetime

@campaign_manager_required
def campaign_manager_home(request):
    return render(request, "campaign/manager_home.html")

@campaign_manager_required
def campaign_list(request):
    """
    Display a paginated list of all campaigns with search and filtering.
    """
    campaigns = Campaign.objects.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(campaigns, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'campaigns': page_obj, 
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }

    return render(request, 'campaign/campaign_details/campaign_list.html', context)


@campaign_manager_required
def create_campaign_step1(request):
    if request.method == 'POST':
        form = CampaignStep1Form(request.POST, request.FILES)
        if form.is_valid():
            session_data = {}
            for key, value in form.cleaned_data.items():
                if key == 'banner_img':
                    session_data[key] = None
                elif key == 'shop' and isinstance(value, Shop):
                    session_data[key] = value.id
                elif isinstance(value, datetime):
                    session_data[key] = timezone.localtime(value).isoformat()
                elif isinstance(value, date):
                    session_data[key] = value.isoformat()
                else:
                    session_data[key] = value

            if 'banner_img' in request.FILES:
                banner_img = request.FILES['banner_img']
                temp_path = default_storage.save(
                    f'temp_banner_imgs/{banner_img.name}',
                    ContentFile(banner_img.read())
                )
                session_data["banner_img_temp_path"] = temp_path
                session_data["banner_img_name"] = banner_img.name 

            request.session["campaign_step1"] = session_data
            request.session.modified = True
            

            return redirect("managementApp:create_campaign_step2")
    else:
        form = CampaignStep1Form()

    return render(request, "campaign/create/step1.html", {"form": form})
        

@campaign_manager_required
def create_campaign_step2(request):
    """
    Step 2: Select existing tasks or create new ones for the campaign.
    """
    # Confirm step1 data exists
    step1_data = request.session.get("campaign_step1")
    if not step1_data:
        return redirect("managementApp:create_campaign_step1")

    # Get up to 5 reusable tasks for this campaign
    available_tasks = Task.objects.filter(
        is_template=False,
        campaign__isnull=True,
        deadline__gte=timezone.localtime(timezone.now()),
        assigned_mentors=CampaignManagerUtils.get_campaign_mentor(),
    )[:5]

    # Allow dynamic formset (0 extra, JS will add more)
    TaskFormSet = modelformset_factory(Task, form=CampaignTaskForm, extra=0, can_delete=True)

    if request.method == "POST":
        selected_task_ids = [int(pk) for pk in request.POST.getlist("existing_tasks") if pk.isdigit()]
        formset = TaskFormSet(request.POST, request.FILES, queryset=Task.objects.none())

        if formset.is_valid():
            new_tasks_data =[
                CampaignManagerUtils.serialize_task_data(form.cleaned_data)
                for form in formset.forms
                if form.cleaned_data and not form.cleaned_data.get("DELETE")
            ]

            if not selected_task_ids and not new_tasks_data:
                #prevent submission with no task selection
                messages.error(request, "יש לבחור לפחות משימה אחת או ליצור חדשה.")
            else:
                request.session["campaign_step2"] = {
                    "selected_task_ids": selected_task_ids
                }
                request.session["new_tasks"] = new_tasks_data
                request.session.modified = True
                return redirect("managementApp:create_campaign_step3")

    else:
        formset = TaskFormSet(queryset=Task.objects.none())

    context = {
        "available_tasks": available_tasks,
        "formset": formset,
    }
    return render(request, "campaign/create/step2.html", context)


@campaign_manager_required
def create_campaign_step3(request):
    """
    Step 3: Finalize campaign creation.
    """
    step1 = request.session.get("campaign_step1")
    step2 = request.session.get("campaign_step2")
    new_tasks_data = request.session.get("new_tasks", [])

    if not step1 or not step2:
        return redirect("managementApp:create_campaign_step1")

    if request.method == "POST":
        banner_img = None
        temp_path = step1.get("banner_img_temp_path")
        if temp_path and default_storage.exists(temp_path):
            # Read file content into memory BEFORE the 'with' closes
            with default_storage.open(temp_path, 'rb') as f:
                file_data = f.read()
                banner_img = ContentFile(file_data, name=os.path.basename(temp_path))
        campaign = CampaignManagerUtils.create_campaign_from_wizard(
            step1=step1,
            step2=step2,
            new_tasks_data=new_tasks_data,
            mentor_user=request.user,
            banner_img=banner_img
        )

        # Clear session
        request.session.pop("campaign_step1", None)
        request.session.pop("campaign_step2", None)
        request.session.pop("new_tasks", None)
        if default_storage.exists(temp_path):
            default_storage.delete(temp_path)
        messages.success(request, "הקמפיין נוצר בהצלחה .")
        return redirect("managementApp:campaign_list")

    # Summary display
    context = {
        "step1": step1,
        "existing_tasks": Task.objects.filter(id__in=step2.get("selected_task_ids", [])),
        "new_tasks": new_tasks_data,
    }
    return render(request, "campaign/create/step3.html", context)


@campaign_manager_required
def campaign_approvals_panel(request):
    """
    Display all recent TaskCompletions (pending / check-in/out) for campaign tasks managed by the virtual mentor.
    """
    CampaignUtils.expire_campaign_reservations()
    mentor = CampaignManagerUtils.get_campaign_mentor()
    recent_date = timezone.localtime(timezone.now()) - timedelta(days=3)

    task_completions = TaskCompletion.objects.filter(
        task__assigned_mentors=mentor,
        task__campaign__isnull=False,
        completion_date__gte=recent_date,
        status__in=["pending", "checked_in", "checked_out"]
    ).select_related("child", "task", "task__campaign").order_by("-completion_date")

    context = {
        "task_completions": task_completions,
    }
    return render(request, "campaign/tasks/approvals_panel.html", context)


@campaign_manager_required
def track_campaign_participants(request, campaign_id):
    """
    Display a list of children who joined the campaign, with progress and option to remove.
    """
    CampaignUtils.expire_campaign_reservations()
    campaign = get_object_or_404(Campaign, id=campaign_id)
    joined_child_ids  = CampaignUtils.current_approved_children_qs(campaign)
    total_children_joined = joined_child_ids.count()
    total_children_finished = 0
    total_tasks = campaign.tasks.count()
    # Compute task progress and time left
    children_data = []
    for child_id in joined_child_ids.values_list('child', flat=True):
        child = Child.objects.get(id=child_id)
        approved_tasks = TaskCompletion.objects.filter(
            child=child,
            task__campaign=campaign,
            status='approved'
        ).count()
        has_child_finished = approved_tasks == total_tasks
        if has_child_finished:
            total_children_finished += 1
        children_data.append({
            "child": child,
            "join_date": CampaignUtils.get_child_join_date(child, campaign),
            "time_left": CampaignUtils.get_time_left(child, campaign),
            "approved_tasks": approved_tasks,
            "total_tasks": total_tasks,
            "progress": int((approved_tasks / total_tasks) * 100) if total_tasks > 0 else 0,
            "has_child_finished": has_child_finished
        })

    context = {
        "campaign": campaign,
        "children_data": children_data,
        "total_children_joined": total_children_joined,
        "total_children_finished": total_children_finished
    }
    return render(request, "campaign/campaign_details/track.html", context)


@require_POST
@campaign_manager_required
def remove_child_from_campaign(request, campaign_id, child_id):
    """
    Remove a child from a campaign.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    child = get_object_or_404(Child, id=child_id)

    CampaignUtils.leave_campaign(child, campaign)

    return redirect("managementApp:track_campaign_participants", campaign_id=campaign.id)
