import json
from django.shortcuts import get_object_or_404
from shopApp.models import Reward, Redemption, RedemptionRequest, Shop
from childApp.models import Child
from teenApp.utils.NotificationManager import NotificationManager
from childApp.utils.TeenCoinManager import TeenCoinManager  
from Volunteen.constants import MAX_REWARDS_PER_DAY, REDEMPTION_REQUEST_EXPIRATION_MINUTES
from django.utils.timezone import now, localdate
from django.db.models import Sum
import random
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from shopApp.utils.ShopDonationUtils import ShopDonationUtils
class ShopManager:
    
    @staticmethod
    def get_random_digits(n=3):
        return ''.join(str(random.randint(0, 9)) for _ in range(n))
    
    @staticmethod
    def get_all_shop_rewards(shop_id):
        """
        Returns a list of all rewards available at a shop.
        """
        return Reward.objects.filter(shop=shop_id)
    
    @staticmethod
    def get_all_visible_rewards(shop_id):
        """
        Returns a list of all visible rewards available at a shop.
        """
        return Reward.objects.filter(shop=shop_id, is_visible=True)
    
    @staticmethod
    def get_points_used_this_month(shop: Shop) -> int:
        """
        Returns the total points used by the shop this month.
        """
        # Beginning of this month (zeroing out time for reliability)
        start_of_month = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sum all points used from Redemptions in the current month
        points_used_this_month = Redemption.objects.filter(
            shop=shop,
            date_redeemed__gte=start_of_month
        ).aggregate(total_points=Sum('points_used'))['total_points'] or 0

        total_donation_spending_this_month = ShopDonationUtils.get_monthly_donation_spending_for_shop(shop)
        return points_used_this_month + total_donation_spending_this_month

    @staticmethod
    def get_remaining_points_this_month(shop: Shop) -> int:
        """
        Calculates how many points the shop has left for the current month.
        This is done by:
          - Setting start_of_month to day=1
          - Summing all points used via Redemption since start_of_month
          - Summing all points used via DonationSpending since start_of_month
          - Including locked points
          - Subtracting that sum from shop.max_points
        """
        # Beginning of this month (zeroing out time for reliability)
        start_of_month = now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sum all points used from Redemptions in the current month
        points_used_this_month = Redemption.objects.filter(
            shop=shop,
            date_redeemed__gte=start_of_month
        ).aggregate(total_points=Sum('points_used'))['total_points'] or 0

        locked_points_this_month = shop.locked_usage_this_month
        total_donation_spending_this_month = ShopDonationUtils.get_monthly_donation_spending_for_shop(shop)
        # Remaining = max_points - used points
        remaining_points = max(0, shop.max_points - points_used_this_month - locked_points_this_month - total_donation_spending_this_month)
        return remaining_points
    
    @staticmethod
    def redeem_teencoins_for_rewards(child, shop, selected_rewards):
        """
        Handles the logic of redeeming TeenCoins for rewards at a shop.
        Ensures:
        - The child has enough TeenCoins (from the past 3 months).
        - The shop’s monthly limit is not exceeded.
        - Redemptions follow FIFO deduction.
        - A redemption record is created.
        """
        today = localdate()
        
        redemptions_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)
        total_rewards_today = redemptions_today.count()
        points_spent_today = redemptions_today.aggregate(total_points=Sum('points_used'))['total_points'] or 0

        # Calculate requested rewards and total points needed
        total_rewards_requested = sum(r['quantity'] for r in selected_rewards)
        total_points_needed = sum(r['quantity'] * r['points'] for r in selected_rewards)

        # Check if reward count and points exceed the daily limit
        if total_rewards_requested > MAX_REWARDS_PER_DAY:
            return {"status": "error", "message": f"ניתן לרכוש מקסימום {MAX_REWARDS_PER_DAY} פרסים בפעולה אחת."}

        if total_rewards_today + total_rewards_requested > MAX_REWARDS_PER_DAY:
            return {"status": "error", "message": "הילד הגיע למגבלת הנקודות היומית של החנות."}

        # Enforce shop's monthly redemption limit
        remaining_points = ShopManager.get_remaining_points_this_month(shop)
        total_points_needed = sum(r['quantity'] * r['points'] for r in selected_rewards)

        if total_points_needed > remaining_points:
            return {"status": "error", "message": "החנות עברה את מגבלת הנקודות החודשית."}

        # Check if child has enough TeenCoins using TeenCoinManager
        if TeenCoinManager.get_total_active_teencoins(child) < total_points_needed:
            return {"status": "error", "message": "אין מספיק נקודות ברשותך."}

        # Deduct TeenCoins FIFO-style using TeenCoinManager
        try:
            TeenCoinManager.redeem_teencoins(child, total_points_needed)
            points_used = 0
            redemptions = []

            for reward in selected_rewards:
                reward_obj = get_object_or_404(Reward, id=reward['reward_id'])
                points_used += reward['quantity'] * reward['points']
                redemption = Redemption.objects.create(
                    child=child,
                    reward=reward_obj,
                    points_used=reward['quantity'] * reward['points'],
                    shop=reward_obj.shop,
                    quantity=reward['quantity']
                )
                redemptions.append({
                    "title": reward_obj.title,
                    "points_used": reward['quantity'] * reward['points'],
                    "quantity": reward['quantity'],
                    "points": reward['points']
                })

            # Send notification if child has an email
            if child.user.email:
                NotificationManager.sent_mail(
                    f'שלום {child.user.first_name}, הרכישה שלך הושלמה. ניצלת {points_used} נקודות.',
                    child.user.email
                )

            return {"status": "success", "points_used": points_used, "redemptions": redemptions}

        except ValueError as e:
            return {"status": "error", "message": str(e)}
    
    
    @staticmethod
    def can_redeem_rewards(child, shop, selected_rewards, is_approval=False):
        """
        Checks if a child can redeem the requested rewards based on daily limits, available TeenCoins,
        and the shop’s monthly limit.
        """
        
        today = localdate()

        # Include only pending requests created within the last REDEMPTION_REQUEST_EXPIRATION_MINUTES
        recent_pending_requests = RedemptionRequest.objects.filter(
            child=child, shop=shop, date_requested__date=today, status="pending",
            locked_at__gte=timezone.now() - timedelta(minutes=REDEMPTION_REQUEST_EXPIRATION_MINUTES)
        )
        recent_pending_requests_count=0
        for req in recent_pending_requests:
            recent_pending_requests_count+=req.quantity

        total_redemption_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)
        total_rewards_today=0
        for redemption in total_redemption_today:
            total_rewards_today+=redemption.quantity
        total_rewards_requested = sum(r['quantity'] for r in selected_rewards)
        if is_approval:
            if total_rewards_today + total_rewards_requested> MAX_REWARDS_PER_DAY:
                return {"status": "error", "message": "הילד הגיע למגבלות הרכישות היומיות."}
        else:
            if total_rewards_today + recent_pending_requests_count + total_rewards_requested > MAX_REWARDS_PER_DAY:
                return {"status": "error", "message": "הילד הגיע למגבלות הרכישות היומיות."}

        total_points_needed = sum(r['quantity'] * r['points'] for r in selected_rewards)
        if TeenCoinManager.get_total_active_teencoins(child) < total_points_needed:
            return {"status": "error", "message": "אין לך מספיק טינקואינס לביצוע הרכישה."}

        # Check shop’s available monthly limit (including locked points)
        shop_remaining_points = ShopManager.get_remaining_points_this_month(shop)

        if total_points_needed > shop_remaining_points:
            return {"status": "error", "message": "החנות עברה את מגבלת הנקודות החודשית."}

        return {"status": "success", "message": "הבקשה תקפה וניתן לבצע מימוש."}
    
    
    
    
    
    @staticmethod
    def approve_multiple_children(shop, requests_qs):
        """
        Takes a queryset of RedemptionRequest objects (all 'pending', same shop),
        groups them by child, and attempts to approve them child by child.

        Returns a structure like:
        {
            "status": "success" or "partial_success" or "error",
            "results": [
                {
                    "child_id": <child.id>,
                    "status": "success" or "error",
                    "message": "Approved all" or "Not enough points" etc.
                },
                ...
            ]
        }
        """
        grouped_by_child = defaultdict(list)
        for req in requests_qs:
            grouped_by_child[req.child].append(req)
        
        results = []
        overall_status = "success"

        for child, child_requests in grouped_by_child.items():
            # Build selected_requests structure
            selected_requests = []
            for r in child_requests:
                selected_requests.append({
                    'reward_id': r.reward.id,
                    'quantity': r.quantity,
                    'points': r.reward.points_required,
                    'request_id': r.id
                })
            
            # Validate
            check_result = ShopManager.can_redeem_rewards(child, shop, selected_requests, is_approval=True)
            if check_result["status"] == "error":
                # Mark all requests from this child as failing
                results.append({
                    "child_id": child.id,
                    "status": "error",
                    "message": check_result["message"]
                })
                overall_status = "partial_success"
                continue
            
            # Approve (deduct points, create redemptions)
            approval_result = ShopManager.approve_redemption_requests(child, selected_requests)
            if approval_result["status"] == "error":
                results.append({
                    "child_id": child.id,
                    "status": "error",
                    "message": approval_result["message"]
                })
                overall_status = "partial_success"
                continue

            # Mark each request as approved
            for r in child_requests:
                r.status = 'approved'
                r.save()

            results.append({
                "child_id": child.id,
                "status": "success",
                "message": f"Approved {len(child_requests)} requests for child {child}"
            })

        return {
            "status": overall_status,
            "results": results
        }
    
    
    @staticmethod
    def approve_redemption_requests(child, selected_requests):
        """
        Approves a set of redemption requests for a child.
        
        :param child: Child object.
        :param selected_requests: List of dictionaries with keys:
             - reward_id: ID of the reward.
             - quantity: Number of items requested.
             - points: Points per unit.
        :return: Dictionary with status, total points used, and details of created redemptions, or an error message.
        """
        total_points_needed = sum(item['quantity'] * item['points'] for item in selected_requests)
        if TeenCoinManager.get_total_active_teencoins(child) < total_points_needed:
            return {"status": "error", "message": "אין מספיק נקודות ברשותך."}
        
        try:
            TeenCoinManager.redeem_teencoins(child, total_points_needed)
            points_used = 0
            redemptions = []
            
            for item in selected_requests:
                reward_obj = get_object_or_404(Reward, id=item['reward_id'])
                current_points = item['quantity'] * item['points']
                points_used += current_points
                
                redemption = Redemption.objects.create(
                    child=child,
                    reward=reward_obj,
                    points_used=current_points,
                    shop=reward_obj.shop,
                    quantity=item['quantity']
                )
                redemptions.append({
                    "title": reward_obj.title,
                    "points_used": current_points,
                    "quantity": item['quantity'],
                    "points": item['points']
                })
            
            if child.user.email:
                NotificationManager.sent_mail(
                    f'שלום {child.user.first_name}, הרכישה שלך הושלמה. ניצלת {points_used} נקודות.',
                    child.user.email
                )
            
            return {"status": "success", "points_used": points_used, "redemptions": redemptions}
        
        except ValueError as e:
            return {"status": "error", "message": str(e)}
    
    
    @staticmethod
    def reject_redemption_requests(redemption_requests):
        """
        Rejects a set of pending redemption requests.
        
        :param redemption_requests: QuerySet or list of RedemptionRequest objects to reject.
        :return: Dictionary with status and a message.
        """
        try:
            for req in redemption_requests:
                req.status = 'rejected'
                req.save()
            return {"status": "success", "message": "הבקשות נדחו בהצלחה."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        
    @staticmethod
    def expire_old_requests():
        """
        Expires all pending redemption requests older than REDEMPTION_REQUEST_EXPIRATION_MINUTES m.
        For each expired request:
            - Marks it as 'expired'
            - Returns the locked points to the child's balance
            - Unlocks the points from the shop's monthly limit
        Returns:
            The number of requests that were expired.
        """
        expiration_threshold = timezone.now() - timedelta(minutes=REDEMPTION_REQUEST_EXPIRATION_MINUTES)
        expired_requests = RedemptionRequest.objects.filter(
            status='pending',
            locked_at__lt=expiration_threshold
        )
        expired_count = expired_requests.count()

        for req in expired_requests:
            req.status = 'expired'
            # Unlock the locked points from the shop's monthly usage
            req.shop.unlock_monthly_points(req.locked_points)
            req.save()

        return expired_count
