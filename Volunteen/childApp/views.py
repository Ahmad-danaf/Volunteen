from django.shortcuts import render,get_object_or_404,redirect
from datetime import datetime
from django.db.models import Sum, F, Prefetch 
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.templatetags.static import static
from django.utils.timezone import now
from django.utils import timezone
from teenApp.interface_adapters.forms import DateRangeForm,DateRangeCityForm
import json
from datetime import datetime, date, timedelta
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from shopApp.models import Redemption, Shop, Reward, Category,RedemptionRequest
from teenApp.entities.TaskCompletion import TaskCompletion
from django.utils.timezone import localdate
from .forms import RedemptionRatingForm
from django.utils.timezone import now
from django.http import HttpResponseForbidden
from Volunteen.constants import AVAILABLE_CITIES, MAX_REWARDS_PER_DAY,POINTS_PER_LEVEL,LEVELS
from childApp.utils.TeenCoinManager import TeenCoinManager
from shopApp.utils.shop_manager import ShopManager
from childApp.utils.child_task_manager import ChildTaskManager
from childApp.utils.ChildRedemptionManager import ChildRedemptionManager
from childApp.utils.leaderboard_manager import LeaderboardUtils

def child_landing(request):
    top_children = LeaderboardUtils.get_children_leaderboard(limit=3)
    return render(request, 'child_landing.html', {'top_children': top_children})


@login_required
def child_home(request):
    child = Child.objects.select_related("user").get(user=request.user)

    current_day = datetime.now().weekday()
    current_day = (current_day + 1) % 7  # Adjust for 0-Sunday format
    greetings = {
        0: f"שיהיה לך פתיחה חזקה לשבוע! תתחיל לאסוף נקודות ולהגשים את החלומות שלך!",  # יום ראשון
        1: f"זה יום שני! תמשיך לשאוף למעלה ולכוון גבוה! אתה בדרך להצלחה!",
        2: f"זה יום שלישי! הזמן להראות את הכוח והנחישות שלך! אתה יכול לעשות הכל!",
        3: f"זה יום רביעי! אתה כבר באמצע השבוע, תמשיך להתקדם ולכבוש מטרות!",
        4: f"זה יום חמישי! כמעט סיימת את השבוע, תשמור על קצב חזק ותגיע למטרה!",
        5: f"שישי שמח! תחגוג את ההישגים שלך ותהנה מהיום! אתה בדרך הנכונה!",  # יום שישי
        6: f"זה יום שבת! תמשיך לפעול ולהתקדם לקראת שבוע חדש ומוצלח!",
    }
    todays_greeting = greetings[current_day]
    new_tasks = ChildTaskManager.get_new_assigned_tasks(child)
    new_tasks_count = ChildTaskManager.get_new_assigned_tasks_count(child)

    if request.method == 'POST' and 'close_notification' in request.POST:
        for task in new_tasks:
            ChildTaskManager.mark_task_as_viewed(child, task)

    def calculate_progress(child):
        points_needed_for_next_level = POINTS_PER_LEVEL
        return (child.points % points_needed_for_next_level) / points_needed_for_next_level * POINTS_PER_LEVEL
    
    progress_to_next_level = calculate_progress(child)

    active_points = TeenCoinManager.get_total_active_teencoins(child)
    return render(request, 'child_home.html', {
        'child': child,
        'active_points': active_points,
        'greeting': todays_greeting,
        'new_tasks_count': new_tasks_count,
        'new_tasks': new_tasks,
        'level_name': LEVELS[child.level],
        'level': child.level,
        'progress_percent': progress_to_next_level  # Pass the computed percentage to the template
    })

@login_required
def update_streak(request):
    """Update the child's daily streak progress if they haven't already checked in today."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    child = Child.objects.select_related("user").get(user=request.user)
    today = date.today()

    if child.last_streak_date == today:
        return JsonResponse({"message": "כבר לחצת היום!", "streak": child.streak_count, "success": False})

    # Update streak count based on the last streak date
    if child.last_streak_date == today - timedelta(days=1):
        child.streak_count += 1  # Continue streak
    else:
        child.streak_count = 1  # Reset streak

    child.last_streak_date = today
    child.save()

    return JsonResponse({"message": "🔥 כל הכבוד! שמרת על הרצף!", "streak": child.streak_count, "success": True})

@login_required
def top_streaks(request):
    top_children = Child.objects.order_by('-streak_count')[:10]
    return render(request, "streak_leaderboard.html", {"top_children": top_children})

@login_required
def child_redemption_history(request):
    child = Child.objects.get(user=request.user)
    form = DateRangeForm(request.GET or None)
    redemptions = ChildRedemptionManager.get_all_redemptions(child)
    default_date = date(2201, 1, 1)  

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = None
        end_date = None

    if start_date and end_date:
        redemptions = ChildRedemptionManager.get_redemptions_in_date_range(child, start_date, end_date)

    return render(request, 'child_redemption_history.html', {'redemptions': redemptions, 'form': form})

@login_required
def rate_redemption_view(request, redemption_id):
    redemption = get_object_or_404(Redemption, id=redemption_id, child=request.user.child)

    # Check if the redemption is within the 7-day scope and not already rated
    if not redemption.can_rate():
        return HttpResponseForbidden("לא ניתן לדרג מימוש זה. ייתכן שחלפו 7 ימים או שהמימוש כבר דורג.")

    if request.method == 'POST':
        form = RedemptionRatingForm(request.POST, instance=redemption)
        
        if form.is_valid():
            form.save() 
            return redirect('childApp:child_redemption_history')  
    else:
        form = RedemptionRatingForm(instance=redemption)

    return render(request, 'rate_redemption.html', {
        'form': form,
        'redemption': redemption,
        'stars_range':range(1, 6)
    })
    
@login_required
def child_completed_tasks(request):
    """Retrieve and display all completed tasks for a child with optional date filtering."""
    
    child = Child.objects.select_related("user").get(user=request.user)
    form = DateRangeForm(request.GET or None)

    # Retrieve completed tasks
    task_completions = ChildTaskManager.get_completed_tasks(child).select_related("task").prefetch_related("task__assigned_mentors")

    # Apply date filter if form is valid
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        task_completions = task_completions.filter(completion_date__range=(start_date, end_date))

    tasks_with_bonus = [
        {
            'title': task_completion.task.title,
            'points': task_completion.task.points,
            'completion_date': task_completion.completion_date,
            'mentor': ", ".join(mentor.user.username for mentor in task_completion.task.assigned_mentors.all())
        }
        for task_completion in task_completions
    ]
    
    return render(request, 'child_completed_tasks.html', {'tasks_with_bonus': tasks_with_bonus, 'form': form})

@login_required
def child_active_list(request):
    try:
        child = Child.objects.get(user=request.user)
        assignments = ChildTaskManager.get_all_child_active_tasks(child)
        

        return render(request, 'child_active_list.html', {'assignments': assignments})
    
    except Child.DoesNotExist:
        return render(request, 'list_tasks.html', {'error': 'You are not authorized to view this page.'})


@login_required
def child_points_history(request):
    """Retrieve and display the child's point history including completed tasks and redemptions."""
    # Get the child's instance via the one-to-one relation with User
    child = request.user.child

    task_completions = TeenCoinManager.get_expiration_schedule(child)

    # Retrieve the redemption history for the child, most recent first.
    redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')

    # Pass both lists to the template.
    context = {
        'task_completions': task_completions,  # Earned coins (green transactions)
        'redemptions': redemptions,            # Redeemed coins (red transactions)
        "active_points": TeenCoinManager.get_total_active_teencoins(child)
    }
    return render(request, 'child_points_history.html', context)

@login_required
def rewards_view(request):
    # Prefetch related rewards for efficiency
    shops = Shop.objects.prefetch_related(
        Prefetch('rewards', queryset=Reward.objects.filter(is_visible=True))
    ).all()

    child = request.user.child
    child_city = child.city if child.city else ''

    # Get available categories
    available_categories = Category.objects.all().values("code", "name")

    shops_with_images = []
    for shop in shops:
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        shop_image = shop.img.url if shop.img else static('images/logo.png')
        points_left_to_spend = shop.max_points - points_used_this_month
        rewards_with_images = [
            {
                'title': reward.title,
                'img_url': reward.img.url if reward.img else static('images/logo.png'),
                'points': reward.points_required,
                'sufficient_points': child.points >= reward.points_required
            }
            for reward in shop.rewards.filter(is_visible=True)
        ]
        
        shops_with_images.append({
            'id': shop.id,
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
        'child_points': child.points,
        'child_city': child_city,
        'available_cities': AVAILABLE_CITIES,
        'categories_list': categories_list, 
    }
    return render(request, 'shop_list.html', context)

@login_required
def shop_rewards_view(request, shop_id):
    """
    Display available rewards for a given shop and allow teens to submit redemption requests.
    """
    child = get_object_or_404(Child, user=request.user)
    shop = get_object_or_404(Shop, id=shop_id)

    # Retrieve all visible rewards for this shop using the utility method
    rewards = ShopManager.get_all_visible_rewards(shop_id)

    # Calculate daily redemption statistics
    today = localdate()
    redemptions_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)
    total_rewards_today = redemptions_today.count()
    total_req_rewards_today =RedemptionRequest.objects.filter(child=child, shop=shop, date_requested__date=today).count()

    # Calculate remaining daily limits
    remaining_rewards = max(0, MAX_REWARDS_PER_DAY - total_rewards_today- total_req_rewards_today)

    # Get the child's total available TeenCoins (active, unexpired)
    available_teencoins = TeenCoinManager.get_total_active_teencoins(child)

    # Mark each reward as affordable (or not) based on remaining points and available coins.
    for reward in rewards:
        reward.affordable = reward.points_required <= available_teencoins

    context = {
        "shop": shop,
        "rewards": rewards,
        "remaining_rewards": remaining_rewards,
        "available_teencoins": available_teencoins,
    }
    return render(request, 'shop_rewards.html', context)

@csrf_protect
def submit_redemption_request(request):
    """
    Handles the child's redemption request for a reward.
    - Uses `can_redeem_rewards` to validate limits.
    - Creates a `RedemptionRequest` if valid.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

    try:
        data = json.loads(request.body)
        child = get_object_or_404(Child, user=request.user)
        shop = get_object_or_404(Shop, id=data.get("shop_id"))
        selected_rewards = data.get("selected_rewards", [])

        if not selected_rewards:
            return JsonResponse({"status": "error", "message": "לא נבחרו פרסים."})

        # Check if the child can redeem these rewards
        validation_result = ShopManager.can_redeem_rewards(child, shop, selected_rewards)
        if validation_result["status"] == "error":
            return JsonResponse(validation_result)

        # Create pending redemption request
        for reward_data in selected_rewards:
            reward = get_object_or_404(Reward, id=reward_data['reward_id'])
            RedemptionRequest.objects.create(
                child=child,
                shop=reward.shop,
                reward=reward,
                quantity=reward_data['quantity'],
                points_used=reward_data['quantity'] * reward.points_required,
                status="pending"
            )

        return JsonResponse({"status": "success", "message": "בקשת המימוש נשלחה בהצלחה!"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": f"שגיאה: {str(e)}"}, status=500)


@require_POST
def cancel_request(request):
    """
    Cancel the current redemption request.
    Clears any pending redemption data from the session and returns a success response.
    """
    # Optional: Clear any session data related to the redemption process
    if 'selected_rewards' in request.session:
        del request.session['selected_rewards']
    return JsonResponse({"status": "ok"})


@login_required
def points_leaderboard(request):
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

    children = LeaderboardUtils.get_children_leaderboard(start_date, end_date, city)
    return render(request, 'points_leaderboard.html', {'children': children, 'form': form})

@csrf_exempt
def save_phone_number(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone_number = data.get("phone_number")
        
        child = request.user.child
        child.user.phone = phone_number
        child.user.save()

        return json.JsonResponse({"success": True})
    
    return json.JsonResponse({"success": False, "error": "Invalid request"}, status=400)


@login_required
def task_check_in_out(request):
    """Retrieve tasks that require check-in or check-out for the child."""
    child = request.user.child

    # Retrieve assigned tasks that are not completed
    assigned_tasks = ChildTaskManager.get_all_child_active_tasks(child)

    filtered_tasks = []
    for task in assigned_tasks:
        task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
        if not task_completion or not task_completion.checkout_img:
            filtered_tasks.append(task)

    return render(request, 'task_check_in_out.html', {'tasks': filtered_tasks})

@login_required
def check_in(request, task_id):
    """Allow a child to check in to a task."""
    child = request.user.child
    task = get_object_or_404(Task, id=task_id)
    replace_image = request.GET.get('replace_image') == 'true'

    # Check if the child has already checked in
    task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
    if task_completion and task_completion.checkin_img and not replace_image:
        return render(request, 'check_in_exists.html', {'task': task, 'child': child})

    return render(request, 'check_in.html', {'task': task, 'child': child})

@login_required
def check_out(request, task_id):
    """Allow a child to check out from a task only if they checked in first."""
    child = request.user.child
    task = get_object_or_404(Task, id=task_id)

    # Ensure the task was checked in before allowing check-out
    task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
    if not task_completion or not task_completion.checkin_img:
        return render(request, 'check_in_warning.html')

    return render(request, 'check_out.html', {'task': task, 'child': child})

@login_required
def no_check_in(request):
    return render(request, 'check_in_warning.html')

@csrf_exempt
@login_required
def submit_check_in(request):
    """Submit a check-in image for a task."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'שיטה לא נתמכת.'})

    task_id = request.POST.get('task_id')
    image = request.FILES.get('image')

    if not task_id or not image:
        return JsonResponse({'success': False, 'error': 'חסרים נתונים (task_id או image).'})

    child = request.user.child
    task = get_object_or_404(Task, id=task_id)

    task_completion, created = TaskCompletion.objects.get_or_create(task=task, child=child)

    # Save image
    task_completion.checkin_img = default_storage.save(f'checkin_images/{child.id}_{task.id}_checkin.jpg', image)
    task_completion.save()

    return JsonResponse({'success': True, 'message': 'צ\'ק-אין נשמר בהצלחה.'})

@csrf_exempt
@login_required
def submit_check_out(request):
    """Submit a check-out image for a task, ensuring check-in was completed first."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'שיטה לא נתמכת.'})

    task_id = request.POST.get('task_id')
    image = request.FILES.get('image')

    if not task_id or not image:
        return JsonResponse({'success': False, 'error': 'חסרים נתונים (task_id או image).'})

    child = request.user.child
    task = get_object_or_404(Task, id=task_id)

    task_completion, created = TaskCompletion.objects.get_or_create(task=task, child=child)

    if not task_completion.checkin_img:
        return redirect('childApp:no_check_in')

    # Save image
    task_completion.checkout_img = default_storage.save(f'checkout_images/{child.id}_{task.id}_checkout.jpg', image)
    task_completion.status = 'pending'
    task_completion.save()

    return JsonResponse({'success': True, 'message': 'צ\'ק-אאוט נשמר. ההמתנה לאישור המנטור.'})

@login_required
def mark_tasks_as_viewed(request):
    """Mark all new tasks as viewed for a child."""
    if request.method == "POST":
        child = request.user.child
        TaskAssignment.objects.filter(child=child, is_new=True).update(is_new=False)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)
