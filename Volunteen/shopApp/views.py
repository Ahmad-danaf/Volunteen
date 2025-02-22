from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from childApp.models import Child
from shopApp.models import Reward
from django.http import JsonResponse
from shopApp.models import Redemption
from shopApp.models import Shop, OpeningHours,RedemptionRequest
from .forms import IdentifyChildForm
import random
from datetime import datetime
from django.utils.timezone import now,localdate
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
import json
from django.views.decorators.http import require_POST
from teenApp.utils import NotificationManager
from django.contrib import messages
from .utils.shop_manager import ShopManager
from collections import defaultdict

@login_required
def shop_redeem_points(request):
    if request.method == 'POST':
        if 'selected_rewards' in request.POST:
            selected_rewards = request.POST.get('selected_rewards')
            request.session['selected_rewards'] = selected_rewards
            return redirect('shopApp:shop_identify_child')
        
    shop = Shop.objects.get(user=request.user)
    now = datetime.now()
    start_of_month = now.replace(day=1)
    redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
    points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
    remaining_points = shop.max_points - points_used_this_month

    rewards = Reward.objects.filter(
        shop=shop,
        points_required__lte=remaining_points
    )

    return render(request, 'shop_redeem_points.html', {'rewards': rewards, 'remaining_points': remaining_points})


@login_required
def shop_identify_child(request):
    id_form = IdentifyChildForm()

    if request.method == 'POST':
        id_form = IdentifyChildForm(request.POST)
        if id_form.is_valid():
            identifier = id_form.cleaned_data['identifier']
            secret_code = id_form.cleaned_data['secret_code']
            try:
                child = Child.objects.get(identifier=identifier, secret_code=secret_code)
                # Update secret code
                child.secret_code=get_random_digits()
                child.save()
                request.session['child_id'] = child.id
                return redirect('shopApp:shop_complete_transaction')
            except Child.DoesNotExist:
                return render(request, 'shop_invalid_identifier.html', {'id_form': id_form})

    return render(request, 'shop_identify_child.html', {'id_form': id_form})


@login_required
def shop_complete_transaction(request):
    # Extract child ID from session
    child_id = request.session.get('child_id')
    if not child_id:
        return redirect('shopApp:shop_identify_child')

    # Extract selected rewards from session
    selected_rewards_json = request.session.get('selected_rewards')
    if not selected_rewards_json:
        return redirect('shopApp:shop_redeem_points')

    selected_rewards = json.loads(selected_rewards_json)
    child = get_object_or_404(Child, id=child_id)
    shop = get_object_or_404(Shop, user=request.user)

    # Call the utility class for redemption logic
    result = ShopManager.redeem_teencoins_for_rewards(child, shop, selected_rewards)

    if result["status"] == "error":
        return render(request, 'shop_redemption_error.html', {"message": result["message"]})

    # Clear session data after successful redemption
    request.session['selected_rewards'] = json.dumps([])
    request.session.pop('child_id', None)

    return render(request, 'shop_redemption_success.html', {
        "child": child,
        "points_used": result["points_used"],
        "receipt": result["redemptions"],
    })
    
@login_required
def shop_cancel_transaction(request):
    # Clear session data related to the transaction
    request.session.pop('child_id', None)
    request.session['selected_rewards'] = json.dumps([])
    return JsonResponse({'status': 'ok'})

@login_required
def shop_home(request):
    shop = Shop.objects.get(user=request.user)
    start_of_month = now().replace(day=1)
    redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
    points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
    points_left_to_redeem = max(0, shop.max_points - points_used_this_month)

    context = {
        'shop': shop,
        'points_used_this_month': points_used_this_month,
        'points_left_to_redeem': points_left_to_redeem,
    }
    return render(request, 'shop_home.html', context)

def get_random_digits(n=3):
    return ''.join(str(random.randint(0, 9)) for _ in range(n))

@login_required
def shop_redemption_history(request):
    shop = request.user.shop
    redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')
    monthly_redemptions = (
        redemptions.annotate(month=TruncMonth('date_redeemed'))
                   .values('month')
                   .annotate(total_points=Sum('points_used'))
                   .annotate(max_points=F('shop__max_points')) 
                   .order_by('-month')
    )

    last_redemptions = redemptions[:10]  # Get the last 10 redemptions

    context = {
        'shop': shop,
        'monthly_redemptions': monthly_redemptions,
        'recent_redemptions': last_redemptions,
    }
    return render(request, 'shop_redemption_history.html', context)

@require_POST
def toggle_reward_visibility(request, reward_id):
    reward = get_object_or_404(Reward, id=reward_id)
    
    if request.user == reward.shop.user:  # Ensure the user is the shop owner
        reward.is_visible = not reward.is_visible
        reward.save()
        return JsonResponse({'success': True, 'is_visible': reward.is_visible})
    
    return JsonResponse({'success': False}, status=403)


@login_required
def opening_hours_view(request):
    shop = request.user.shop
    opening_hours = OpeningHours.objects.filter(shop=shop)
    days_of_week_dict = {0: 'ראשון', 1: 'שני', 2: 'שלישי', 3: 'רביעי', 4: 'חמישי', 5: 'שישי', 6: 'שבת'}

    # Convert opening hours to a dictionary for easy rendering in the template
    hours_dict = {
        day: {
            'day_name': days_of_week_dict[day],
            'opening_hour': None,
            'closing_hour': None
        } for day in range(7)  # 0-6 for Sunday to Saturday
    }

    for entry in opening_hours:
        hours_dict[entry.day]['opening_hour'] = entry.opening_hour.strftime('%H:%M') if entry.opening_hour else None
        hours_dict[entry.day]['closing_hour'] = entry.closing_hour.strftime('%H:%M') if entry.closing_hour else None

    if request.method == 'POST':
        try:
            for day in range(7):
                opening_hour = request.POST.get(f'opening_hour_{day}')
                closing_hour = request.POST.get(f'closing_hour_{day}')

                # If both fields are empty, delete the entry (mark as closed)
                if not opening_hour and not closing_hour:
                    OpeningHours.objects.filter(shop=shop, day=day).delete()
                else:
                    OpeningHours.objects.update_or_create(
                        shop=shop,
                        day=day,
                        defaults={
                            'opening_hour': opening_hour,
                            'closing_hour': closing_hour
                        }
                    )
            messages.success(request, 'שעות הפתיחה עודכנו בהצלחה!')
        except Exception as e:
            messages.error(request, f'שגיאה בעדכון שעות הפתיחה: {str(e)}')

        return redirect('shopApp:opening_hours')

    return render(request, 'opening_hours.html', {
        'shop': shop,
        'hours_dict': hours_dict
    })
    
    
    
def pending_redemption_requests(request):
    """
    Retrieves today's pending redemption requests for the current shop,
    groups them by child, and aggregates totals for each child.
    """
    # Get the shop for the currently logged in user
    shop = get_object_or_404(Shop, user=request.user)
    today = localdate()

    # Query all pending redemption requests for today for this shop
    requests_qs = RedemptionRequest.objects.filter(
        shop=shop,
        status='pending',
        date_requested__date=today
    ).select_related('child', 'reward')

    # Group requests by child using a dictionary
    grouped_requests = defaultdict(list)
    for req in requests_qs:
        grouped_requests[req.child].append(req)

    # Build an aggregated summary per child
    aggregated = []
    for child, req_list in grouped_requests.items():
        total_requests = sum(req.quantity for req in req_list)
        total_points = sum(req.points_used for req in req_list)
        aggregated.append({
            'child': child,
            'requests': req_list,
            'total_requests': total_requests,
            'total_points': total_points,
        })

    # Optionally sort the aggregated list (for example, by child's first name)
    aggregated.sort(key=lambda x: x['child'].user.first_name)

    context = {
        'aggregated_requests': aggregated,
        'today': today,
    }
    return render(request, 'pending_requests.html', context)


@login_required
@require_POST
def process_request(request):
    """
    Processes an individual pending redemption request.
    Expects a JSON payload with:
      - request_id: the ID of the RedemptionRequest
      - action: "approve" or "reject"
    """
    try:
        data = json.loads(request.body)
        req_id = data.get('request_id')
        action = data.get('action')

        if not req_id or action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": "Invalid parameters."}, status=400)

        # Get the redemption request ensuring it's pending.
        redemption_req = get_object_or_404(RedemptionRequest, id=req_id, status='pending')
        
        # Ensure the request belongs to the currently logged-in shop.
        shop = get_object_or_404(Shop, user=request.user)
        if redemption_req.shop != shop:
            return JsonResponse({"status": "error", "message": "Unauthorized access."}, status=403)
        
        # Process the action
        if action == "approve":
            redemption_req.approve() 
        elif action == "reject":
            redemption_req.reject()
        
        return JsonResponse({"status": "success", "message": "Request processed successfully."})
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def batch_process_requests(request):
    """
    Processes all pending redemption requests for a specific child for the current shop.
    Expects a JSON payload with:
      - child_id: the ID of the child whose requests should be processed.
      - action: "approve" or "reject" (applied to all pending requests for that child).
    """
    try:
        data = json.loads(request.body)
        child_id = data.get('child_id')
        action = data.get('action')

        if not child_id or action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": "Invalid parameters."}, status=400)

        # Get the current shop
        shop = get_object_or_404(Shop, user=request.user)

        # Get all pending requests for this child and shop
        pending_requests = RedemptionRequest.objects.filter(child__id=child_id, shop=shop, status='pending')
        if not pending_requests.exists():
            return JsonResponse({"status": "error", "message": "No pending requests found for this child."}, status=404)

        # Process each request according to the specified action
        for req in pending_requests:
            if action == "approve":
                req.approve()
            elif action == "reject":
                req.reject()

        return JsonResponse({"status": "success", "message": "Batch processing successful."})
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)