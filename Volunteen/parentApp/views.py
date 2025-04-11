from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Parent,ChildSubscription
from childApp.models import Child
from teenApp.entities.task import Task
from django.shortcuts import get_object_or_404
from django.utils import timezone
from childApp.utils.child_task_manager import ChildTaskManager
from childApp.utils.ChildRedemptionManager import ChildRedemptionManager
from childApp.utils.TeenCoinManager import TeenCoinManager
from shopApp.utils.shop_manager import ShopManager
from django.db.models import Prefetch, Sum
from django.utils.timezone import now
from django.templatetags.static import static
from shopApp.models import Shop, Reward, Redemption, Category
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from Volunteen.constants import AVAILABLE_CITIES
from childApp.utils.LeaderboardUtils import LeaderboardUtils
from teenApp.interface_adapters.forms import DateRangeCityForm
from parentApp.utils.ParentTaskUtils import ParentTaskUtils
from django.http import HttpResponseForbidden, HttpResponseBadRequest, JsonResponse, HttpResponseNotFound
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.views.decorators.http import require_POST

@login_required
def inactive_home(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    return render(request, 'parentApp/inactive_home.html', {'child': child})

def parent_landing(request):
    return render(request, 'parent_landing.html')

@login_required
def child_selection(request):
    """
    Render a page showing cards for each child.
    Each card displays a few summary details so the parent can choose a child.
    """
    # Assuming the parent's children are available as a related manager
    parent = Parent.objects.get(user=request.user)
    
    # Fetch all children linked to the parent
    children_obj = Child.objects.filter(parent=parent)
    children = list(children_obj)
    # Annotate each child with some summary details
    for child in children:
        child.assigned_tasks_count = ChildTaskManager.get_assigned_tasks_count(child)
        child.completed_tasks_count = ChildTaskManager.get_completed_tasks_count(child)
        child.teen_coins_used = ChildRedemptionManager.get_teen_coins_used(child)
        if hasattr(child, 'subscription') and child.subscription:
            child.can_show_expiration_warning = child.subscription.can_show_expiration_warning()
            child.is_subscription_active = child.subscription.is_active()
        else:
            child.can_show_expiration_warning = False
            child.is_subscription_active = False

    context = {
        'user_children': children,
    }
    return render(request, 'child_selection.html', context)


@login_required
def parent_dashboard(request,child_id):
    # Fetch the parent object
    parent = Parent.objects.get(user=request.user)
    
    selected_child  = get_object_or_404(Child, id=child_id)
    
    # Fetch summary data using your utility classes
    mentor_assigned_tasks_count = ChildTaskManager.get_mentor_assigned_tasks_count(selected_child)
    mentor_completed_tasks_count = ChildTaskManager.get_mentor_completed_tasks_count(selected_child)
    parent_assigned_tasks_count = ParentTaskUtils.get_assigned_tasks_count(selected_child)
    parent_completed_tasks_count = ParentTaskUtils.get_completed_tasks_count(selected_child)
    teen_coins_used = ChildRedemptionManager.get_teen_coins_used(selected_child)

    context = {
        'selected_child': selected_child,
        'selected_child_id': selected_child.id,
        'mentor_assigned_tasks_count': mentor_assigned_tasks_count,
        'mentor_completed_tasks_count': mentor_completed_tasks_count,
        'parent_assigned_tasks_count': parent_assigned_tasks_count,
        'parent_completed_tasks_count': parent_completed_tasks_count,
        'teen_coins_used': teen_coins_used,
    }
    return render(request, 'parent_dashboard.html', context)


@login_required
def mentor_task_dashboard(request, child_id):
    # Fetch the child object
    child = get_object_or_404(Child, id=child_id)

    # Get filters from request
    status_filter = request.GET.get('status', 'all')  # 'all', 'completed', 'pending'
    date_filter = request.GET.get('date', 'all')  # 'all', 'today', 'this_week', 'this_month'

    # Retrieve filtered tasks using the utility class
    filtered_tasks = ChildTaskManager.get_mentor_tasks_by_status_date(child, status_filter, date_filter)
    context = {
        'child': child,
        'all_tasks': filtered_tasks,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'mentor_task_dashboard.html', context)


@login_required
def redeemtion_dashboard(request, child_id):
    """
    Renders the Parent Redemption Rewards dashboard for the selected child.
    
    This view ensures that the child belongs to the logged-in parent
    and passes both the child's details and the available rewards to the template.
    """
    child = get_object_or_404(Child, id=child_id)
    redemptions = ChildRedemptionManager.get_all_redemptions(child)
    curr_child_points = TeenCoinManager.get_total_active_teencoins(child)
    context = {
        'child': child,
        'redemptions': redemptions,
        'curr_child_points': curr_child_points,
    }
    return render(request, 'child_redeemtion_dashboard.html', context)


@login_required
def all_rewards(request, child_id):
    # Prefetch related rewards for efficiency
    shops = Shop.objects.filter(is_active=True).prefetch_related(
    Prefetch('rewards', queryset=Reward.objects.filter(is_visible=True))
    )

    child = get_object_or_404(Child, id=child_id)
    child_city = child.city if child.city else ''

    # Get available categories
    available_categories = Category.objects.all().values("code", "name")

    shops_with_images = []
    for shop in shops:
        points_used_this_month = ShopManager.get_points_used_this_month(shop)
        shop_image = shop.img.url if shop.img else static('images/logo.png')
        points_left_to_spend = ShopManager.get_remaining_points_this_month(shop)
        rewards_with_images = [
            {
                'title': reward.title,
                'img_url': reward.img.url if reward.img else static('images/logo.png'),
                'points': reward.points_required,
                'sufficient_points': TeenCoinManager.get_total_active_teencoins(child) >= reward.points_required
            }
            for reward in shop.rewards.filter(is_visible=True)
        ]
        
        shops_with_images.append({
            'name': shop.name,
            'img': shop_image,
            'city': shop.city,  
            'rewards': rewards_with_images,
            'used_points': points_used_this_month,
            'is_open': shop.is_open(),
            'points_left_to_spend': points_left_to_spend,
            'categories': [cat.code for cat in shop.categories.all()]  # Add categories
        })
    categories_list = []
    for cat in available_categories:
        code, name = cat['code'], cat['name']
        categories_list.append({'code': code, 'name': name})
                            
    context = {
        'shops': shops_with_images,
        'child_points': TeenCoinManager.get_total_active_teencoins(child),
        'child_city': child_city,
        'available_cities': AVAILABLE_CITIES,
        'categories_list': categories_list, 
    }
    return render(request, 'parent_reward_list.html', context)


@login_required
def all_children_points_leaderboard(request,child_id):
    selected_child  = get_object_or_404(Child, id=child_id)
    form = DateRangeCityForm(request.GET or None)
    if form.is_valid():
        city = form.cleaned_data.get('city')  
        if form.cleaned_data['start_date'] and form.cleaned_data['end_date']:
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            start_date, end_date = LeaderboardUtils.convert_dates_to_datetime_range(start_date, end_date)
        else:
            start_date = None
            end_date = None
    else:
        city = None
        start_date = None
        end_date = None

    children = LeaderboardUtils.get_children_leaderboard(
    start_date=start_date,
    end_date=end_date,
    institution=selected_child.institution,
    city=city
)
    return render(request, 'all_children_points_leaderboard.html', {'children': children, 'form': form})


@login_required
def parent_tasks_view(request):
    """
    View for parent to manage tasks - both create new tasks and view/approve existing ones.
    This view supports four tabs:
    1. Active tasks - Tasks assigned but not yet started
    2. Pending review - Tasks in progress (pending, checked_in)
    3. Completed tasks - Tasks that have been approved
    4. Rejected tasks - Tasks that have been rejected
    By default, shows tasks within a 3-month window (past month, current month, next month).
    Can filter tasks by date range if specified in the request.
    """
    # Get the parent object
    try:
        parent = request.user.parent
    except Parent.DoesNotExist:
        return HttpResponseForbidden("Only parents can access this view.")
    
    children = ParentTaskUtils.get_children(parent)
    children_list = [{
        "id": child.id,
        "name": child.user.username,  
        "selected": False
    } for child in children]
    
    # Get all tasks created by this parent and filter out any that have been refunded
    assignments = ParentTaskUtils.get_tasks_assigned_by_parent(parent).filter(refunded_at__isnull=True)
    
    # Setup default date filtering (past month, current month, next month)
    today = datetime.today().date()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_next_month = today + relativedelta(months=1, day=31)

    # Get filters from request
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    show_all = request.GET.get("show_all") == "true"

    # Parse user-defined date filters if provided
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
    except ValueError:
        start_date, end_date = None, None  # Ignore invalid inputs

    # Apply default date range if no filters are provided and show_all is False
    if not show_all:
        start_date = start_date or first_day_last_month
        end_date = end_date or last_day_next_month

    # Convert to template-friendly format
    date_filter = {
        "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
        "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
        "show_all": show_all,
    }

    # Filter assignments 
    if not show_all:
        assignments = assignments.filter(task__deadline__range=(start_date, end_date))
        
    # Dictionaries to store tasks grouped by task ID or completion ID
    active_tasks_dict = {}
    pending_tasks_dict = {}
    completed_tasks_dict = {}
    rejected_tasks_dict = {}  
    
    # Process assignments and group them by task
    for assignment in assignments:
        task = assignment.task
        
        # Get all related task completions for this assignment
        task_completions = TaskCompletion.objects.filter(
            task=task, 
            child=assignment.child
        )
        
        if not task_completions.exists():
            # This task is active but not started yet
            if task.id not in active_tasks_dict:
                # Initialize task with first child
                active_tasks_dict[task.id] = {
                    "id": task.id,
                    "name": task.title,
                    "description": task.description,
                    "points": task.points,
                    "dueDate": task.deadline.strftime("%Y-%m-%d"),
                    "status": "active",
                    "isEditable": task.deadline > today,
                    "assignedTo": [assignment.child.id],
                    "assignmentIds": [assignment.id],
                    "children": [{
                        "id": assignment.child.id,
                        "name": assignment.child.user.username
                    }],
                    "allowSoftDelete": True
                }
            else:
                # Add additional child to existing task
                active_tasks_dict[task.id]["assignedTo"].append(assignment.child.id)
                active_tasks_dict[task.id]["assignmentIds"].append(assignment.id)
                active_tasks_dict[task.id]["children"].append({
                    "id": assignment.child.id,
                    "name": assignment.child.user.username
                })
        else:
            # Get the most recent task completion
            completion = task_completions.latest('completion_date')
            
            if completion.status in ['pending', 'checked_in','checked_out']:
                # Task is in progress and pending review
                pending_tasks_dict[completion.id] = {
                    "id": task.id,
                    "name": task.title,
                    "description": task.description,
                    "points": task.points,
                    "dueDate": task.deadline.strftime("%Y-%m-%d"),
                    "status": completion.status,
                    "isEditable": False,
                    "assignedTo": [assignment.child.id],
                    "assignmentId": assignment.id,
                    "completionId": completion.id,
                    "childName": completion.child.user.username,
                    "childId": completion.child.id,
                    "checkin_img": completion.checkin_img.url if completion.checkin_img else None,
                    "checkout_img": completion.checkout_img.url if completion.checkout_img else None
                }
            elif completion.status == 'approved':
                # Task is completed - each completion is handled separately
                completed_tasks_dict[completion.id] = {
                    "id": task.id,
                    "name": task.title,
                    "description": task.description,
                    "points": task.points,
                    "dueDate": task.deadline.strftime("%Y-%m-%d"),
                    "status": "completed",
                    "isEditable": False,
                    "assignedTo": [assignment.child.id],
                    "assignmentId": assignment.id,
                    "completionId": completion.id,
                    "childName": completion.child.user.username,
                    "childId": completion.child.id,
                    "completedDate": completion.completion_date.strftime("%Y-%m-%d") if completion.completion_date else None
                }
            elif completion.status == 'rejected':
                # Task is rejected - add it to the rejected tasks dictionary
                rejected_tasks_dict[completion.id] = {
                    "id": task.id,
                    "name": task.title,
                    "description": task.description,
                    "points": task.points,
                    "dueDate": task.deadline.strftime("%Y-%m-%d"),
                    "status": "rejected",
                    "isEditable": False,
                    "assignedTo": [assignment.child.id],
                    "assignmentId": assignment.id,
                    "completionId": completion.id,
                    "childName": completion.child.user.username,
                    "childId": completion.child.id,
                    "rejectedDate": completion.completion_date.strftime("%Y-%m-%d") if completion.completion_date else None
                }
    
    # Convert dictionaries to lists for the frontend
    active_tasks = list(active_tasks_dict.values())
    pending_tasks = list(pending_tasks_dict.values())
    completed_tasks = list(completed_tasks_dict.values())
    rejected_tasks = list(rejected_tasks_dict.values())
    
    # Combine all task lists into a structure for the frontend
    all_tasks = {
        "active": active_tasks,
        "pending": pending_tasks,
        "completed": completed_tasks,
        "rejected": rejected_tasks
    }
    
    context = {
        "children_json": json.dumps(children_list),
        "parent_tasks_json": json.dumps(all_tasks),
        "date_filter_json": json.dumps(date_filter),
        "available_teencoins": parent.available_teencoins,
    }
    return render(request, "parent_tasks.html", context)

@login_required
def create_parent_task(request):
    """
    Handles creating a new task assignment by the parent.
    Expects a JSON payload with:
      - name: Task title
      - description: Task description
      - points: Task points (and cost)
      - dueDate: Due date (YYYY-MM-DD)
      - selectedChildren: List of child IDs (that belong to the parent)
      
    The parent's available teencoins must be sufficient; otherwise an error is returned.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    try:
        parent = request.user.parent
    except Parent.DoesNotExist:
        return HttpResponseForbidden("Only parents can create tasks.")
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        description = data.get('description')
        points = int(data.get('points', 0))
        due_date = data.get('dueDate')
        selected_children = data.get('selectedChildren', [])
        
        # Validate the data
        if not name or not description or points <= 0 or not due_date or not selected_children:
            return JsonResponse({"success": False, "message": "נתונים חסרים או לא תקינים."}, status=400)
        
        # Check if parent has enough teencoins
        total_cost = points * len(selected_children)
        if parent.available_teencoins < total_cost:
            return JsonResponse({
                "success": False, 
                "message": f"אין מספיק TEENCoins. נדרש: {total_cost}, זמין: {parent.available_teencoins}."
            }, status=400)
           
        task, assignments = ParentTaskUtils.create_and_assign_task(
            parent=parent,
            name=name,
            description=description,
            points=points,
            due_date=due_date,
            selected_children=selected_children
        )

        # Get list of children with names for the response
        children_list = []
        assignment_ids = []
        for assignment in assignments:
            children_list.append({
                "id": assignment.child.id,
                "name": assignment.child.user.username
            })
            assignment_ids.append(assignment.id)
        
        # Return success response with the new task data
        return JsonResponse({
            "success": True,
            "message": "המשימה נוצרה בהצלחה!",
            "task": {
                "id": task.id,
                "name": task.title,
                "description": task.description,
                "points": task.points,
                "dueDate": task.deadline.strftime("%Y-%m-%d"),
                "status": "pending",
                "assignedTo": [assignment.child.id for assignment in assignments],
                "assignmentIds": assignment_ids,
                "children": children_list
            },
            "updatedTeencoins": parent.available_teencoins
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "פורמט JSON לא תקין."}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"שגיאה: {str(e)}"}, status=500)
    
    
@login_required
def edit_task(request, task_id):
    # Ensure the user is a parent.
    try:
        parent = request.user.parent
    except Parent.DoesNotExist:
        return HttpResponseForbidden("Only parents can access this view.")
    
    # Verify that the task belongs to this user (using TaskAssignment as a proxy)
    assignment = TaskAssignment.objects.filter(task__id=task_id, assigned_by=request.user).first()
    if not assignment:
        return HttpResponseNotFound("Task not found or you do not have permission to edit it.")
    
    task = assignment.task
    today = datetime.today().date()
    
    # Only allow editing if the task's deadline has not passed.
    if task.deadline < today:
        return JsonResponse({"success": False, "message": "לא ניתן לערוך משימה שתאריך היעד שלה עבר."})
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "JSON not valid."})
        
        # Use current values if no new value is provided (partial update).
        new_title = data.get("title", task.title)
        new_description = data.get("description", task.description)
        
        # Process deadline if provided; otherwise, use the current deadline.
        if "deadline" in data:
            deadline_str = data.get("deadline")
            try:
                new_deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"success": False, "message": "פורמט תאריך יעד לא תקין. יש להשתמש ב-YYYY-MM-DD."})
            if new_deadline < today:
                return JsonResponse({"success": False, "message": "תאריך יעד לא יכול להיות בעבר."})
        else:
            new_deadline = task.deadline
        
        # Update the task with the new values.
        task.title = new_title
        task.description = new_description
        task.deadline = new_deadline
        task.save()
        
        return JsonResponse({"success": True, "message": "המשימה עודכנה בהצלחה."})
    else:
        # Return the current task details.
        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "deadline": task.deadline.strftime("%Y-%m-%d"),
        }
        return JsonResponse({"success": True, "task": task_data})
    
@login_required
@require_POST
def refund_task_assignment_view(request):
    try:
        parent=request.user.parent
    except Parent.DoesNotExist:
        return HttpResponseForbidden("Only parents can refund task assignments.")
    try:
        data=json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON.")
    assignment_id=data.get("assignment_id")
    if not assignment_id:
        return JsonResponse({"success": False, "message": "מזהה המשימה חסר.","error":"assignment_id is required"}, status=400)
    
    try:
        assignment=TaskAssignment.objects.get(id=assignment_id,refunded_at__isnull=True)
    except TaskAssignment.DoesNotExist:
        return JsonResponse({"success": False, "message": "משימה לא נמצאה או כבר נדחתה.","error":"assignment not found or already refunded"}, status=404)
    
    if assignment.assigned_by != request.user:
        return JsonResponse({"success": False, "message": "אין לך הרשאה להחזיר משימה זו.","error":"you do not have permission to refund this task"}, status=403)
    try:
        ParentTaskUtils.refund_task_assignment(assignment,parent)
    except ValueError as e:
        return JsonResponse({"success": False, "message": str(e),"error":str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e),"error":str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "message": "Task refunded successfully for the selected child.",
        "refunded_assignment_id": assignment.id
    }) 
    
@login_required
def approve_task_completion(request):
    """
    Handles the approval of a task completion by a parent.
    Expects a JSON payload with:
      - completionId: The ID of the TaskCompletion to approve
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")
    
    try:
        parent = request.user.parent
    except Parent.DoesNotExist:
        return HttpResponseForbidden("Only parents can approve tasks.")
    
    try:
        data = json.loads(request.body)
        completion_id = data.get('completionId')
        
        if not completion_id:
            return JsonResponse({"success": False, "message": "מזהה השלמת משימה חסר."}, status=400)
        
        try:
            task_completion = TaskCompletion.objects.get(id=completion_id)
            
            # Verify that this completion is for a child of this parent
            if task_completion.child.parent != parent:
                return JsonResponse({"success": False, "message": "אין לך הרשאה לאשר משימה זו."}, status=403)
            
            # Approve the task completion
            ParentTaskUtils.approve_task_completion(parent.user, task_completion)
            
            # Get updated points for the child using TeenCoinManager
            child_points = TeenCoinManager.get_total_active_teencoins(task_completion.child)
            
            return JsonResponse({
                "success": True,
                "message": "המשימה אושרה בהצלחה!",
                "updatedCompletionStatus": "approved",
                "childPoints": child_points,
            })
            
        except TaskCompletion.DoesNotExist:
            return JsonResponse({"success": False, "message": "השלמת המשימה לא נמצאה."}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "פורמט JSON לא תקין."}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"שגיאה: {str(e)}"}, status=500)
    
@login_required
def reject_task_completion(request):
    """
    Handles the rejection of a task completion by a parent.
    Expects a JSON payload with:
        - completionId: The ID of the TaskCompletion to reject
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")
    
    try:
        parent = request.user.parent
    except Parent.DoesNotExist: 
        return HttpResponseForbidden("Only parents can reject task completions.")
    
    try:
        data = json.loads(request.body)
        completion_id = data.get('completionId')
        feedback = data.get('feedback', '')
        
        if not completion_id:
            return JsonResponse({"success": False, "message": "מזהה השלמת משימה חסר."}, status=400)
        
        try:
            task_completion = TaskCompletion.objects.get(id=completion_id)
            
            # Verify that this completion is for a child of this parent
            if task_completion.child.parent != parent:
                return JsonResponse({"success": False, "message": "אין לך הרשאה לדחות משימה זו."}, status=403)
            
            # Reject the task completion using your utility method
            ParentTaskUtils.reject_task_completion(request.user, task_completion, feedback)
            
            return JsonResponse({
                "success": True,
                "message": "המשימה נדחתה בהצלחה!",
                "updatedCompletionStatus": "rejected",
            })
        except TaskCompletion.DoesNotExist:
            return JsonResponse({"success": False, "message": "השלמת המשימה לא נמצאה."}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "JSON not valid."}, status=400)
    except Exception as e:
        # Log exception if needed
        return JsonResponse({"success": False, "message": f"שגיאה: {str(e)}"}, status=500)
    
    
@login_required
def donation_leaderboard(request):
    """
    Displays a leaderboard of children based on their donation amounts.
    By default, shows current month's donations, but allows filtering by date range and city.
    """
    form = DateRangeCityForm(request.GET or None)
    
    if form.is_valid():
        city = form.cleaned_data.get('city', "ALL")
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        
        donations = LeaderboardUtils.get_donations_leaderboard(
            start_date=start_date,
            end_date=end_date,
            city=city
        )
    else:
        donations = LeaderboardUtils.get_donations_leaderboard(city="ALL")
    
    return render(request, 'parentApp/donation/donation_leaderboard.html', {
        'donations': donations,
        'form': form,
    })
   
