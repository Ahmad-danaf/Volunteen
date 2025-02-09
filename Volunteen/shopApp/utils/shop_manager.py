import json
from django.utils.timezone import now, localdate
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from shopApp.models import Redemption, Reward, Shop
from childApp.models import Child
from teenApp.utils import NotificationManager
from childApp.utilities.TeenCoinManager import TeenCoinManager  
from Volunteen.constants import MAX_TEENCOINS_PER_DAY_SHOPPING
class ShopManager:
    
    @staticmethod
    def redeem_teencoins_for_rewards(child, shop, selected_rewards):
        """
        Handles the logic of redeeming TeenCoins for rewards at a shop.
        Ensures:
        - The child has enough TeenCoins (from the past 3 months).
        - The shop’s monthly limit is not exceeded.
        - Redemptions follow FIFO deduction.
        - A redemption record is created.

        :param child: Child object
        :param shop: Shop object
        :param selected_rewards: List of reward objects with quantities
        :return: Dictionary with success or error details
        """

        today = localdate()
        
        redemptions_today = Redemption.objects.filter(child=child, shop=shop, date_redeemed__date=today)
        total_rewards_today = redemptions_today.count()
        points_spent_today = redemptions_today.aggregate(total_points=Sum('points_used'))['total_points'] or 0

        # Calculate requested rewards and total points needed
        total_rewards_requested = sum(r['quantity'] for r in selected_rewards)
        total_points_needed = sum(r['quantity'] * r['points'] for r in selected_rewards)

        # Check if reward count and points exceed the daily limit
        if total_rewards_requested > 2:
            return {"status": "error", "message": "ניתן לרכוש מקסימום 2 פרסים בפעולה אחת."}

        if total_rewards_today + total_rewards_requested > 2 and points_spent_today + total_points_needed > MAX_TEENCOINS_PER_DAY_SHOPPING:
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
