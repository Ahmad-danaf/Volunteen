from django.shortcuts import render,get_object_or_404,redirect
from datetime import datetime
from django.db.models import Sum, F, Prefetch 
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django_q.tasks import async_task  
from django.views.decorators.csrf import csrf_protect
from django.templatetags.static import static
from django.utils.timezone import now
from django.utils import timezone
from teenApp.interface_adapters.forms import DateRangeForm,DateRangeCityForm,CityDateRangeForm
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
from .forms import RedemptionRatingForm,DonationForm
from django.utils.timezone import now
from django.http import HttpResponseForbidden
from Volunteen.constants import (
    AVAILABLE_CITIES, MAX_REWARDS_PER_DAY,POINTS_PER_LEVEL,LEVELS,SPECIAL_UPLOAD_PERMISSIONS_FOR_CHILDREN,
    CHILDREN_REQUIRE_DEFAULT_IMAGE,REDEMPTION_REQUEST_EXPIRATION_MINUTES,MAX_SHOPS_PER_DAY
)
from childApp.utils.TeenCoinManager import TeenCoinManager
from shopApp.utils.shop_manager import ShopManager
from childApp.utils.child_task_manager import ChildTaskManager
from childApp.utils.ChildRedemptionManager import ChildRedemptionManager
from childApp.utils.LeaderboardUtils import LeaderboardUtils
from teenApp.utils.TaskManagerUtils import TaskManagerUtils
from childApp.utils.check_in_out_utils import process_check_in, process_check_out
from childApp.utils.child_level_management import calculate_total_points
from managementApp.models import DonationCategory, DonationTransaction
from childApp.decorators import child_subscription_required
from parentApp.models import ChildSubscription

def child_landing(request):
    top_children = LeaderboardUtils.get_children_leaderboard(limit=3)
    return render(request, 'child_landing.html', {'top_children': top_children})

@login_required
def inactive_home(request, child_id):
    child = get_object_or_404(Child, id=child_id)
    active_points = TeenCoinManager.get_total_active_teencoins(child)

    return render(request, 'childApp/inactive_home.html', {'child': child,'active_points':active_points})

@login_required
def child_home(request):
    child = Child.objects.select_related("user").get(user=request.user)
    if not hasattr(child, 'subscription'):
        return redirect('childApp:inactive_home', child_id=child.id)
    if child.subscription and not child.subscription.is_active():
        return redirect('childApp:inactive_home', child_id=child.id)
    
    if child.level > child.last_level_awarded:
        TaskManagerUtils.auto_approve_increase_level_for_child(child)
        child.last_level_awarded = child.level
        child.save()
    total_points = calculate_total_points(child)
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

    def calculate_progress(child,points):
        points_needed_for_next_level = POINTS_PER_LEVEL
        return (points % points_needed_for_next_level) / points_needed_for_next_level * POINTS_PER_LEVEL
    
    active_points = TeenCoinManager.get_total_active_teencoins(child)
    progress_to_next_level = calculate_progress(child,total_points)

    LeaderboardUtils.get_current_streak(child)
    return render(request, 'child_home.html', {
        'child': child,
        'active_points': active_points,
        'greeting': todays_greeting,
        'new_tasks_count': new_tasks_count,
        'new_tasks': new_tasks,
        'level_name': LEVELS[child.level],
        'level': child.level,
        'progress_percent': progress_to_next_level,
        'can_show_expiration_warning': child.subscription.can_show_expiration_warning(),
        'days_left_to_expire': max(child.subscription.days_left(),1)
    })
    
@login_required
def donate_coins(request):
    """
    View for donating TeenCoins to various categories.
    GET: Displays the donation form with available categories
    POST: Processes the donation if valid
    """
    child = request.user.child
    available_teencoins = TeenCoinManager.get_total_active_teencoins(child)
    
    # Process donation form submission
    if request.method == 'POST':
        form = DonationForm(request.POST)
        
        if form.is_valid():
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']
            note = form.cleaned_data['note']
            # Validate that the child has enough coins
            if amount > available_teencoins:
                form.add_error('amount', f"אין לך מספיק טינקוינס. יש לך רק {available_teencoins} טינקוינס זמינים.")
            else:
                try:
                    # Redeem the coins using TeenCoinManager
                    redeemed_records = TeenCoinManager.redeem_teencoins(child, amount)
                    
                    # Create a donation transaction record
                    donation = DonationTransaction.objects.create(
                        child=child,
                        category=category,
                        amount=amount,
                        note=note
                    )
                    
                    # Redirect to success page with animation
                    return render(request, 'donation_success.html', {
                        'donation': donation,
                        'category': category.name,
                        'category_description': category.description,
                        'amount': amount
                    })
                    
                except ValueError as e:
                    # Handle insufficient coins error (though we already checked above)
                    form.add_error(None, f"שגיאה בתרומה")
                    print(e)
        
        
        return render(request, 'donate_coins.html', {
            'form': form, 
            'available_teencoins': available_teencoins,
            'categories': categories,
            'error': True
        })
    
    # GET request - display the donation form
    else:
        form = DonationForm()
        
        # Get active donation categories
        categories = DonationCategory.objects.filter(is_active=True)
        
        return render(request, 'donate_coins.html', {
            'form': form,
            'categories': categories,
            'available_teencoins': available_teencoins,
        })


@child_subscription_required
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

@child_subscription_required
def top_streaks(request):
    child = request.user.child
    top_children = LeaderboardUtils.get_top_streaks(institution=child.institution)
    return render(request, "streak_leaderboard.html", {"top_children": top_children})

@child_subscription_required
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

@child_subscription_required
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
    
@child_subscription_required
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
            'mentor': ", ".join(mentor.user.username for mentor in task_completion.task.assigned_mentors.all()),
        }
        for task_completion in task_completions.order_by('-completion_date')
    ]
    
    return render(request, 'child_completed_tasks.html', {'tasks_with_bonus': tasks_with_bonus, 'form': form,'parent_username':child.parent.user.username})

@child_subscription_required
def child_active_list(request):
    try:
        child = Child.objects.get(user=request.user)
        assignments = ChildTaskManager.get_all_child_active_tasks(child)
        

        return render(request, 'child_active_list.html', {'tasks': assignments})
    
    except Child.DoesNotExist:
        return render(request, 'list_tasks.html', {'error': 'You are not authorized to view this page.'})


@child_subscription_required
def child_points_history(request):
    """
    Retrieve and display the child's point history including completed tasks, redemptions, 
    and donation transactions.
    """
    child = request.user.child

    task_completions = TeenCoinManager.get_expiration_schedule(child)

    # Retrieve the redemption history for the child, most recent first.
    redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')
    
    # Retrieve donation transactions for the child, most recent first 
    donations = DonationTransaction.objects.filter(child=child).order_by('-date_donated')

    # Pass both lists to the template.
    context = {
        'task_completions': task_completions,  # Earned coins (green transactions)
        'redemptions': redemptions,            # Redeemed coins (red transactions)
        'donations': donations,              # Donated coins (blue transactions)
        "active_points": TeenCoinManager.get_total_active_teencoins(child)
    }
    return render(request, 'child_points_history.html', context)

@login_required
def rewards_view(request):
    ShopManager.expire_old_requests()
    shops = Shop.objects.filter(is_active=True).prefetch_related(
        Prefetch('rewards', queryset=Reward.objects.filter(is_visible=True))
    )
    child = request.user.child
    child_city = child.city or ''
    available_categories = Category.objects.all().values("code", "name")
    today = localdate()

    # Approved redemptions today (finalized redemptions)
    redeemed_shop_ids = set(
        Redemption.objects.filter(child=child, date_redeemed__date=today)
        .values_list('shop_id', flat=True)
    )

    # Pending redemption requests (still “in process”)
    expiration_threshold = now() - timedelta(minutes=REDEMPTION_REQUEST_EXPIRATION_MINUTES)
    pending_shop_ids = set(
        RedemptionRequest.objects.filter(
            child=child,
            date_requested__date=today,
            status="pending",
            locked_at__gte=expiration_threshold
        ).values_list('shop_id', flat=True)
    )
    shops_used_today = redeemed_shop_ids.union(pending_shop_ids)

    shops_with_data = []
    for shop in shops:
        points_used_this_month = ShopManager.get_points_used_this_month(shop)
        points_left_to_spend = ShopManager.get_remaining_points_this_month(shop)
        
        rewards_data = [
            {
                'title': reward.title,
                'img_url': reward.img.url if reward.img else '',
                'points': reward.points_required,
                'sufficient_points': TeenCoinManager.get_total_active_teencoins(child) >= reward.points_required
            }
            for reward in shop.rewards.all() 
        ]
        
        min_reward = shop.rewards.all().order_by('points_required').first()
        min_points_required = min_reward.points_required if min_reward else 0
        can_redeem_points = points_left_to_spend >= min_points_required

        # Determine if the shop has already been used by the child today.
        shop_used = shop.id in shops_used_today

        # The shop limit is reached if the number of distinct shops used is at or above the maximum
        # and the current shop is not among those already used.
        shop_limit_reached = (len(shops_used_today) >= MAX_SHOPS_PER_DAY) and (not shop_used)

        # Decide overall redeemability with a reason flag.
        if not can_redeem_points:
            can_redeem = False
            reason = "no_rewards_available"  # Shop reached its monthly point cap (or has no visible rewards)
        elif shop_limit_reached:
            can_redeem = False
            reason = "max_shops_reached"      # Child has already used the maximum number of shops today
        else:
            can_redeem = True
            reason = ""

        shops_with_data.append({
            'id': shop.id,
            'name': shop.name,
            'city': shop.city,
            'rewards': rewards_data,
            'used_points': points_used_this_month,
            'is_open': shop.is_open(),
            'points_left_to_spend': points_left_to_spend,
            'categories': [cat.code for cat in shop.categories.all()],
            'can_redeem': can_redeem,
            'reason': reason,
            'img_url': shop.img.url if shop.img else '',
        })

    categories_list = [{'code': cat['code'], 'name': cat['name']} for cat in available_categories]

    context = {
        'shops': shops_with_data,
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
    ShopManager.expire_old_requests()
    child = get_object_or_404(Child, user=request.user)
    shop = get_object_or_404(Shop, id=shop_id, is_active=True)

    # Retrieve all visible rewards for this shop using the utility method
    rewards = ShopManager.get_all_visible_rewards(shop_id)

    # Calculate daily redemption statistics
    today = localdate()
    redemptions_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)
    total_rewards_today = 0
    for redemption in redemptions_today:
        total_rewards_today+=redemption.quantity
    total_req_today =RedemptionRequest.objects.filter(child=child, shop=shop, date_requested__date=today, status="pending")
    total_req_rewards_today=0
    for req in total_req_today:
        total_req_rewards_today+=req.quantity
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
        "MAX_SHOPS_PER_DAY":MAX_SHOPS_PER_DAY
    }
    return render(request, 'shop_rewards.html', context)

@csrf_protect
def submit_redemption_request(request):
    """
    Handles the child's redemption request for a reward.
    - Uses `can_redeem_rewards` to validate limits.
    - Creates a `RedemptionRequest` if valid.
    """
    ShopManager.expire_old_requests()
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

    try:
        data = json.loads(request.body)
        child = get_object_or_404(Child, user=request.user)
        shop = get_object_or_404(Shop, id=data.get("shop_id"))
        selected_rewards = data.get("selected_rewards", [])
        if not shop.is_open():
            return JsonResponse({"status": "error", "message": "החנות אינה פתוחה כעת."})
        if not selected_rewards:
            return JsonResponse({"status": "error", "message": "לא נבחרו פרסים."})

       #check if the child can redeem these rewards
        validation_result = ShopManager.can_redeem_rewards(child, shop, selected_rewards)
        if validation_result["status"] == "error":
            return JsonResponse(validation_result)

        
        total_points_needed = sum(item['quantity'] * item['points'] for item in selected_rewards)

        # Lock shop's monthly points immediately
        shop.lock_monthly_points(total_points_needed)

        now_ts = timezone.now()
        for reward_data in selected_rewards:
            reward = get_object_or_404(Reward, id=reward_data['reward_id'])
            req_points = reward_data['quantity'] * reward.points_required

            RedemptionRequest.objects.create(
                child=child,
                shop=reward.shop,
                reward=reward,
                quantity=reward_data['quantity'],
                points_used=req_points,
                locked_points=req_points,
                locked_at=now_ts,
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


@child_subscription_required
def points_leaderboard(request):
    child = request.user.child
    form = CityDateRangeForm(request.GET or None)

    start_date, end_date, city = None, None, None

    if form.is_valid():
        date_selection = form.cleaned_data['date_range_selection']
        city = form.cleaned_data.get('city', None)

        if date_selection == 'current_month':
            today = timezone.now()
            start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = timezone.now()
        elif date_selection == 'last_month':
            today = timezone.now()
            first_of_this_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_end = first_of_this_month - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date, end_date = last_month_start, last_month_end
        elif date_selection == 'all_time':
            start_date = timezone.make_aware(timezone.datetime(2025, 3, 1, 0, 0))
            end_date = timezone.make_aware(datetime.now())
        else:
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            if start_date and end_date:
                start_date, end_date = LeaderboardUtils.convert_dates_to_datetime_range(start_date, end_date)

    leaderboard_data = LeaderboardUtils.get_custom_leaderboard(
        child,
        start_date=start_date,
        end_date=end_date,
        institution=child.institution,
        city=city,
        top_limit=10
    )
    return render(request, 'points_leaderboard.html', {
        'top_children': leaderboard_data['top_children'],
        'extra_children': leaderboard_data['extra_children'],
        'show_divider': leaderboard_data['show_divider'],
        'form': form,
    })


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


@child_subscription_required
def task_check_in_out(request):
    """Retrieve tasks that require check-in or check-out for the child."""
    child = request.user.child
    today = timezone.now().date()

    # Retrieve assigned tasks that are not completed
    assigned_tasks = (
        ChildTaskManager
        .get_unresolved_tasks_for_child(child)
        .filter(deadline__gte=today)
        .order_by('-is_pinned', 'deadline')
    )
    
    return render(request, 'task_check_in_out.html', {'tasks': assigned_tasks})

@child_subscription_required
def check_in(request, task_id):
    """Allow a child to check in to a task."""
    child = request.user.child
    special_permissions = False
    use_default_image = False
    if child.user.username in SPECIAL_UPLOAD_PERMISSIONS_FOR_CHILDREN:
        special_permissions = True
    if child.user.username in CHILDREN_REQUIRE_DEFAULT_IMAGE:
        use_default_image = True
    task = get_object_or_404(Task, id=task_id)
    replace_image = request.GET.get('replace_image') == 'true'
    
    # Check if the child has already checked in
    task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
    if task_completion and task_completion.checkin_img and not replace_image:
        return render(request, 'check_in_exists.html', {'task': task, 'child': child, 'special_permissions': special_permissions, 'use_default_image': use_default_image})

    return render(request, 'check_in.html', {'task': task, 'child': child, 'special_permissions': special_permissions, 'use_default_image': use_default_image})

@child_subscription_required
def check_out(request, task_id):
    """Allow a child to check out from a task only if they checked in first."""
    child = request.user.child
    special_permissions = False
    use_default_image = False
    if child.user.username in SPECIAL_UPLOAD_PERMISSIONS_FOR_CHILDREN:
        special_permissions = True
    if child.user.username in CHILDREN_REQUIRE_DEFAULT_IMAGE:
        use_default_image = True
    task = get_object_or_404(Task, id=task_id)

    # Ensure the task was checked in before allowing check-out
    task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
    if not task_completion or not task_completion.checkin_img:
        return render(request, 'check_in_warning.html')

    return render(request, 'check_out.html', {'task': task, 'child': child, 'special_permissions': special_permissions, 'use_default_image': use_default_image})

@child_subscription_required
def no_check_in(request):
    return render(request, 'check_in_warning.html')

@csrf_exempt
@child_subscription_required
def submit_check_in(request):
    """Enqueue a background task to process a check-in image."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'שיטה לא נתמכת.'})

    task_id = request.POST.get('task_id')
    image = request.FILES.get('image')
    if not task_id or not image:
        return JsonResponse({'success': False, 'error': 'חסרים נתונים (task_id או image).'})

    child = request.user.child

    # Read the image file into bytes so it can be passed to the task.
    image_data = image.read()

    # Enqueue the task. (child.id and task_id are integers/strings; image_data is bytes.)
    async_task('childApp.utils.check_in_out_utils.process_check_in', child.id, task_id, image_data)

    return JsonResponse({'success': True, 'message': "צ'ק-אין נשלח לעיבוד ברקע."})

@csrf_exempt
@child_subscription_required
def submit_check_out(request):
    """Enqueue a background task to process a check-out image."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'שיטה לא נתמכת.'})

    task_id = request.POST.get('task_id')
    image = request.FILES.get('image')
    if not task_id or not image:
        return JsonResponse({'success': False, 'error': 'חסרים נתונים (task_id או image).'})

    child = request.user.child

    # Read the image file into bytes.
    image_data = image.read()

    # Enqueue the check-out task.
    async_task('childApp.utils.check_in_out_utils.process_check_out', child.id, task_id, image_data)

    return JsonResponse({'success': True, 'message': "צ'ק-אאוט נשלח לעיבוד ברקע."})

@child_subscription_required
def mark_tasks_as_viewed(request):
    """Mark all new tasks as viewed for a child."""
    if request.method == "POST":
        child = request.user.child
        TaskAssignment.objects.filter(child=child, is_new=True).update(is_new=False)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


@login_required
def child_not_approved_requests(request):
    """
    Displays all redemption requests for the logged-in child that are not approved.
    """
    ShopManager.expire_old_requests()
    child = request.user.child  
    pending_requests = ChildRedemptionManager.get_not_approved_requests(child)
    return render(request, "child_not_approved_requests.html", {"requests": pending_requests})


@child_subscription_required
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
    
    return render(request, 'donation_leaderboard.html', {
        'donations': donations,
        'form': form,
    })
   