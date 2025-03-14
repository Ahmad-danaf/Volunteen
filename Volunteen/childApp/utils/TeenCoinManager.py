from django.utils import timezone
from dateutil.relativedelta import relativedelta
from teenApp.entities.TaskCompletion import TaskCompletion
from Volunteen.constants import TEEN_COINS_EXPIRATION_MONTHS
class TeenCoinManager:
    EXPIRATION_DELTA = relativedelta(months=TEEN_COINS_EXPIRATION_MONTHS)

    @staticmethod
    def get_active_task_completions(child):
        """Retrieve approved, unexpired task completions with remaining coins."""
        now = timezone.now()
        return TaskCompletion.objects.filter(
            child=child,
            status='approved',
            completion_date__gte=now - TeenCoinManager.EXPIRATION_DELTA,
            remaining_coins__gt=0  # Only tasks with unused coins
        ).order_by('completion_date')

    @staticmethod
    def get_total_active_teencoins(child):
        """Get total unexpired TeenCoins the child can use."""
        return sum(comp.remaining_coins for comp in TeenCoinManager.get_active_task_completions(child))

    @staticmethod
    def get_expiration_schedule(child):
        """Return details of when each task’s coins will expire."""
        schedule = []
        
        active_completions = TaskCompletion.objects.filter(
            child=child,
            status='approved',
            completion_date__gte=timezone.now() - TeenCoinManager.EXPIRATION_DELTA,
        ).order_by('-completion_date')
        for comp in active_completions:
            schedule.append({
                'task_id': comp.task.id,
                'task_title': comp.task.title,
                'remaining_coins': comp.remaining_coins,
                'completion_date': comp.completion_date,
                'original_points': comp.task.points,
                'bonus_points': comp.bonus_points,
                'expires_on': comp.completion_date + TeenCoinManager.EXPIRATION_DELTA
            })
        return schedule

    @staticmethod
    def redeem_teencoins(child, points_to_redeem):
        """
        Redeem a specific amount of TeenCoins from active tasks, using FIFO order.
        Deducts from the oldest task completions first.

        Returns a list of dictionaries showing which tasks were used and how much was deducted.
        """
        remaining_to_redeem = points_to_redeem
        redeemed_records = []

        active_completions = TeenCoinManager.get_active_task_completions(child)
        total_available = sum(comp.remaining_coins for comp in active_completions)

        # If the child doesn't have enough coins, don't modify any records.
        if total_available < points_to_redeem:
            raise ValueError(f"Not enough TeenCoins to redeem {points_to_redeem}. Available: {total_available}")

        for comp in active_completions:
            if remaining_to_redeem <= 0:
                break

            available = comp.remaining_coins
            if available <= 0:
                continue

            if available >= remaining_to_redeem:
                # Deduct the required points from this task completion.
                comp.remaining_coins -= remaining_to_redeem
                redeemed_records.append({"task_id": comp.task.id, "task_title": comp.task.title, "deducted": remaining_to_redeem})
                remaining_to_redeem = 0
            else:
                # Use up all the points from this task completion.
                redeemed_records.append({"task_id": comp.task.id, "task_title": comp.task.title, "deducted": available})
                remaining_to_redeem -= available
                comp.remaining_coins = 0

            # Save the updated task completion record.
            comp.save()

        return redeemed_records  # Returns a structured list of what was deducted from each task.
