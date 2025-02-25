import json
from django.shortcuts import get_object_or_404
from shopApp.models import Reward, Redemption, RedemptionRequest, Shop
from childApp.models import Child
from teenApp.utils import NotificationManager
from childApp.utils.TeenCoinManager import TeenCoinManager  
from Volunteen.constants import MAX_REWARDS_PER_DAY
from django.utils.timezone import now, localdate
from django.db.models import Sum
class ShopManager:
    
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
            return {"status": "error", "message": "ניתן לרכוש מקסימום 2 פרסים בפעולה אחת."}

        if total_rewards_today + total_rewards_requested > 2:
            return {"status": "error", "message": "הילד הגיע למגבלת הנקודות היומית של החנות."}

        # Enforce shop's monthly redemption limit
        start_of_month = now().replace(day=1)
        points_used_this_month = Redemption.objects.filter(
            shop=shop, date_redeemed__gte=start_of_month
        ).aggregate(total_points=Sum('points_used'))['total_points'] or 0

        remaining_points = shop.max_points - points_used_this_month
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
                    points_used=reward['quantity'] * reward['points'],
                    shop=reward_obj.shop
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
    def can_redeem_rewards(child, shop, selected_rewards):
        """
        Checks if a child can redeem the requested rewards based on daily limits, available TeenCoins,
        and the shop’s monthly limit.
        """
        today = localdate()

        # Fetch the child's redemptions for today (both pending and approved)
        redemptions_today = RedemptionRequest.objects.filter(child=child, shop=shop, date_requested__date=today, status='pending')
        approved_redemptions_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)

        total_rewards_today = redemptions_today.count() + approved_redemptions_today.count()
        approved_total = approved_redemptions_today.aggregate(total_points=Sum('points_used'))['total_points'] or 0

        # Calculate the requested rewards and total points needed
        total_rewards_requested = sum(r['quantity'] for r in selected_rewards)
        total_points_needed = sum(r['quantity'] * r['points'] for r in selected_rewards)

        if total_rewards_requested > MAX_REWARDS_PER_DAY:
            return {"status": "error", "message": "ניתן לרכוש מקסימום 2 פרסים בפעולה אחת."}

        if total_rewards_today + total_rewards_requested > MAX_REWARDS_PER_DAY:
            return {"status": "error", "message": "הילד הגיע למגבלת הנקודות היומית של החנות."}

        if TeenCoinManager.get_total_active_teencoins(child) < total_points_needed:
            return {"status": "error", "message": "אין לך מספיק טינקואינס."}

        start_of_month = now().replace(day=1)
        points_used_this_month = Redemption.objects.filter(
            shop=shop, date_redeemed__gte=start_of_month
        ).aggregate(total_points=Sum('points_used'))['total_points'] or 0

        remaining_points = shop.max_points - points_used_this_month
        if total_points_needed > remaining_points:
            return {"status": "error", "message": "החנות עברה את מגבלת הנקודות החודשית."}

        return {"status": "success", "message": "הבקשה תקפה וניתן לבצע מימוש."}
    
    
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
                    points_used=current_points,
                    shop=reward_obj.shop
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
