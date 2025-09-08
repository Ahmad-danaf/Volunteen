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
from .utils.ShopDonationUtils import ShopDonationUtils

def shop_landing(request):
    return render(request, 'shop_landing.html')


@login_required
def shop_home(request):
    shop = Shop.objects.get(user=request.user)
    points_used_this_month = ShopManager.get_points_used_this_month(shop)
    points_left_to_redeem = ShopManager.get_remaining_points_this_month(shop)
    points_donated_this_month = ShopDonationUtils.get_monthly_donation_spending_for_shop(shop)

    context = {
        'shop': shop,
        'points_used_this_month': points_used_this_month,
        'points_left_to_redeem': points_left_to_redeem,
        'points_donated_this_month': points_donated_this_month,
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
    recent_donations = ShopDonationUtils.get_all_spendings_for_shop(shop,limit=10)

    context = {
        'shop': shop,
        'monthly_redemptions': monthly_redemptions,
        'recent_redemptions': last_redemptions,
        'recent_donations': recent_donations,
    }
    return render(request, 'shop_redemption_history.html', context)

@login_required
def shop_rewards(request):
    shop = request.user.shop
    rewards = ShopManager.get_all_shop_rewards(shop.id)
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

    days_of_week = dict(OpeningHours.DAYS_OF_WEEK)

    raw_hours = OpeningHours.objects.filter(shop=shop).order_by('day', 'opening_hour')
    hours_by_day = {day: [] for day in days_of_week}
    for entry in raw_hours:
        opening = entry.opening_hour.strftime('%H:%M') if entry.opening_hour else ''
        closing = entry.closing_hour.strftime('%H:%M') if entry.closing_hour else ''
        hours_by_day[ entry.day ].append({
            'opening': opening,
            'closing': closing,
        })

    if request.method == 'POST':
        try:
            for day in days_of_week:
                OpeningHours.objects.filter(shop=shop, day=day).delete()
                opens  = request.POST.getlist(f'opening_hour_{day}')
                closes = request.POST.getlist(f'closing_hour_{day}')
                for o, c in zip(opens, closes):
                    if o and c:
                        OpeningHours.objects.create(
                            shop=shop,
                            day=day,
                            opening_hour=o,
                            closing_hour=c
                        )
            messages.success(request, 'שעות הפתיחה עודכנו בהצלחה!')
        except Exception as e:
            messages.error(request, f'שגיאה בעדכון שעות הפתיחה: {e}')
        return redirect('shopApp:opening_hours')

    days = []
    for idx, name in days_of_week.items():
        days.append({
            'index': idx,
            'name': name,
            'slots': hours_by_day.get(idx, []),
        })

    return render(request, 'opening_hours.html', {
        'shop': shop,
        'days': days,
    })
    
    
def pending_redemption_requests(request, public_id):
    """
    Retrieves today's pending redemption requests for the current shop,
    groups them by child, and aggregates totals for each child.
    """
    ShopManager.expire_old_requests()
    shop = get_object_or_404(Shop, public_id=public_id)
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
        'expiration_time': REDEMPTION_REQUEST_EXPIRATION_MINUTES,
        "public_id": public_id,
        "shop_id": shop.id,
    }
    return render(request, 'pending_requests.html', context)

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
        shop_id = int(data.get('shop-id', 0))
        if shop_id == 0:
            return JsonResponse({"status": "error", "message": "Invalid shop ID."}, status=400)
        if not req_id or action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": "Invalid parameters."}, status=400)

        # Retrieve the specific pending request by its ID.
        redemption_req = get_object_or_404(RedemptionRequest, id=req_id, status='pending')
        
        # Ensure the request belongs to the current shop.
        shop = get_object_or_404(Shop, id=shop_id)
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
            result = ShopManager.approve_redemption_requests(redemption_req.child, selected_request,shop)
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
        shop_id = int(data.get('shop-id', 0))
        if shop_id == 0:
            return JsonResponse({"status": "error", "message": "Invalid shop ID."}, status=400)
        if not request_ids or not isinstance(request_ids, list) or action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": "Invalid parameters."}, status=400)

        # Get the current shop.
        shop = get_object_or_404(Shop, id=shop_id)

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
            result = ShopManager.approve_redemption_requests(child, selected_requests,shop)
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

        return JsonResponse({"status": "success", "message": "תהליך  רכישה הושלם"})
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


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
        shop_id = int(data.get("shop-id", 0))
        if shop_id == 0:
            return JsonResponse({"status": "error", "message": "Invalid shop ID."}, status=400)
        # Must be "approve" for this flow
        if action != "approve":
            return JsonResponse({"status": "error", "message": "Invalid action."}, status=400)

        shop = get_object_or_404(Shop, id=shop_id)
        
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
    
@login_required
def shop_donations_details(request):
    # Get the shop associated with the logged-in user
    shop = get_object_or_404(Shop, id=request.user.shop.id)
    
    remaining_points = ShopManager.get_remaining_points_this_month(shop)
    total_spent = ShopDonationUtils.get_total_donation_spending_for_shop(shop)
    spending_by_category = ShopDonationUtils.get_donation_spending_by_category(shop)
    monthly_spent = ShopDonationUtils.get_monthly_donation_spending_for_shop(shop)
    all_spendings = ShopDonationUtils.get_all_spendings_for_shop(shop)
    
    context = {
        'shop': shop,
        'remaining_points': remaining_points,
        'total_spent': total_spent,
        'spending_by_category': spending_by_category,
        'monthly_spent': monthly_spent,
        'all_spendings': all_spendings,
    }
    return render(request, 'shop_donations_details.html', context)