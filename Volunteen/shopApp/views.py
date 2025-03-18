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
from teenApp.utils.NotificationManager import NotificationManager
from django.contrib import messages
from .utils.shop_manager import ShopManager
from collections import defaultdict
from Volunteen.constants import REDEMPTION_REQUEST_EXPIRATION_MINUTES

def shop_landing(request):
    return render(request, 'shop_landing.html')


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

@login_required
def shop_rewards(request):
    shop = request.user.shop
    rewards = Reward.objects.filter(shop=shop)
    context = {
        'shop': shop,
        'rewards': rewards,
    }
    return render(request, 'shop_your_rewards.html', context)


@login_required
def shop_redemptions_view(request):
    shop = get_object_or_404(Shop, user=request.user)
    # Retrieve all redemption transactions for the shop, latest first
    redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')
    
    context = {
        'shop': shop,
        'redemptions': redemptions,
    }
    return render(request, 'shop_redemptions.html', context)

@require_POST
def toggle_reward_visibility(request, reward_id): # if the reward is visible, make it invisible and vice versa
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
    
    
@login_required
def pending_redemption_requests(request):
    """
    Retrieves today's pending redemption requests for the current shop,
    groups them by child, and aggregates totals for each child.
    """
    ShopManager.expire_old_requests()
    shop = get_object_or_404(Shop, user=request.user)
    today = localdate()

    requests_qs = RedemptionRequest.objects.filter(
        shop=shop,
        status='pending',
        date_requested__date=today
    ).select_related('child', 'reward')

    grouped_requests = defaultdict(list)
    for req in requests_qs:
        grouped_requests[req.child].append(req)

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

    aggregated.sort(key=lambda x: x['child'].user.username)

    context = {
        'aggregated_requests': aggregated,
        'today': today,
        'expiration_time': REDEMPTION_REQUEST_EXPIRATION_MINUTES
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

        # Retrieve the specific pending request by its ID.
        redemption_req = get_object_or_404(RedemptionRequest, id=req_id, status='pending')
        
        # Ensure the request belongs to the current shop.
        shop = get_object_or_404(Shop, user=request.user)
        if redemption_req.shop != shop:
            return JsonResponse({"status": "error", "message": "Unauthorized access."}, status=403)
        
        if action == "approve":
            # Build a list for the single request.
            selected_request = [{
                'reward_id': redemption_req.reward.id,
                'quantity': redemption_req.quantity,
                'points': redemption_req.reward.points_required
            }]
            check_result = ShopManager.can_redeem_rewards(redemption_req.child, shop, selected_request, is_approval=True)
            if check_result["status"] == "error":
                return JsonResponse(check_result, status=400)
            result = ShopManager.approve_redemption_requests(redemption_req.child, selected_request)
            if result["status"] == "error":
                return JsonResponse(result, status=400)
            # Mark this specific request as approved.
            redemption_req.status = 'approved'
            redemption_req.save()
        elif action == "reject":
            # Use the reject utility for a list containing this request.
            result = ShopManager.reject_redemption_requests([redemption_req])
            if result["status"] == "error":
                return JsonResponse(result, status=400)
        
        return JsonResponse({"status": "success", "message": "Request processed successfully."})
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def batch_process_requests(request):
    """
    Processes a batch of pending redemption requests specified by their IDs for the current shop.
    Expects a JSON payload with:
      - request_ids: a list of RedemptionRequest IDs to process.
      - action: "approve" or "reject" (applied to each request in the list).
    """
    try:
        data = json.loads(request.body)
        request_ids = data.get('request_ids')
        action = data.get('action')
        if not request_ids or not isinstance(request_ids, list) or action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": "Invalid parameters."}, status=400)

        # Get the current shop.
        shop = get_object_or_404(Shop, user=request.user)

        # Get all pending requests with the given IDs, ensuring they belong to the current shop.
        pending_requests = RedemptionRequest.objects.filter(id__in=request_ids, shop=shop, status='pending').filter(date_requested__date=localdate())
        if not pending_requests.exists():
            return JsonResponse({"status": "error", "message": "No pending requests found with the given IDs."}, status=404)

        if action == "approve":
            # Build a list of request data from the pending requests.
            selected_requests = []
            for req in pending_requests:
                selected_requests.append({
                    'reward_id': req.reward.id,
                    'quantity': req.quantity,
                    'points': req.reward.points_required,
                    'request_id': req.id,
                })
            
            child = pending_requests.first().child
            check_result = ShopManager.can_redeem_rewards(child, shop, selected_requests, is_approval=True)
            if check_result["status"] == "error":
                return JsonResponse(check_result, status=400)
            result = ShopManager.approve_redemption_requests(child, selected_requests)
            if result["status"] == "error":
                return JsonResponse(result, status=400)
            # Mark each processed request as approved.
            for req in pending_requests:
                req.status = 'approved'
                req.save()
        elif action == "reject":
            result = ShopManager.reject_redemption_requests(pending_requests)
            if result["status"] == "error":
                return JsonResponse(result, status=400)

        return JsonResponse({"status": "success", "message": "Batch processing successful."})
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@require_POST
def approve_all_pending_requests(request):
    """
    Approves all pending redemption requests for the current shop,
    grouped by child. Returns partial success if some children fail.
    Expects a JSON payload:
        { "request_ids": [1, 2, 3, ...] }
    """
    try:
        data = json.loads(request.body)
        request_ids = data.get("request_ids", [])  
        action = data.get("action", "approve")     # default to 'approve'
        
        # Must be "approve" for this flow
        if action != "approve":
            return JsonResponse({"status": "error", "message": "Invalid action."}, status=400)
        
        shop = get_object_or_404(Shop, user=request.user)
        
        # If no request_ids provided, you could default to all pending requests for the shop
        if request_ids:
            requests_qs = RedemptionRequest.objects.filter(
                id__in=request_ids, shop=shop, status='pending'
            )
        else:
            return JsonResponse({"status": "error", "message": "לא ניתן לאשר את כל הבקשות לכולם"}, status=400)
        
        if not requests_qs.exists():
            return JsonResponse({"status": "error", "message": "לא ניתן לאשר את כל הבקשות לכולם"}, status=404)
        
        result = ShopManager.approve_multiple_children(shop, requests_qs)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)