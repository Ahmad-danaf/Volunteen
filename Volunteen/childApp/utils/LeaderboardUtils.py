from django.db.models import Sum, Case, When, Value, IntegerField, F
from django.utils import timezone
from childApp.models import Child
from teenApp.entities.TaskCompletion import TaskCompletion
from managementApp.models import DonationTransaction
from .child_level_management import calculate_total_points  
from datetime import datetime, time,date, timedelta

class LeaderboardUtils:
    @staticmethod
    def convert_dates_to_datetime_range(start_date, end_date):
        """
        Converts start_date and end_date to a datetime range.
        """
        start_datetime = datetime.combine(start_date, time.min)  # 00:00:00
        end_datetime = datetime.combine(end_date, time.max)       # 23:59:59
        
        if timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(start_datetime)
        if timezone.is_naive(end_datetime):
            end_datetime = timezone.make_aware(end_datetime)
        return start_date, end_date
    
    
    @staticmethod
    def get_donations_leaderboard(start_date=None, end_date=None, limit=None):
        """
        Returns a queryset (or list) of top donors based on DonationTransaction amounts.
        
        If start_date and end_date are provided, the leaderboard is calculated over that date range.
        Otherwise, it defaults to using the current month (from the 1st day until now).
        
        Each entry contains the child's id, username, and total donated amount.
        """
        now = timezone.now()
        if not start_date or not end_date:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        
        # Ensure dates are timezone-aware
        start_datetime, end_datetime = LeaderboardUtils.convert_dates_to_datetime_range(start_date, end_date)
        
        qs = (DonationTransaction.objects
              .filter(date_donated__range=(start_datetime, end_datetime))
              .values('child__id', 'child__user__username')
              .annotate(total_donated=Sum('amount'))
              .order_by('-total_donated'))
        
        if limit:
            qs = qs[:limit]
        return qs
    
    
    @staticmethod
    def get_children_leaderboard(start_date=None, end_date=None, city=None, limit=None):
        """
        Returns a queryset of Child objects annotated with total points from approved tasks.
        
        - If start_date and end_date are provided, it calculates points earned within that range.
        - Otherwise, it defaults to using the current month (from the 1st day until now).
        - Optionally, a limit (e.g., top 3) can be applied.
        - If a city (other than "ALL") is provided, the queryset is filtered by that city.
        """

        if start_date and end_date:
            qs = Child.objects.all().annotate(
                total_points=Sum(
                    Case(
                        When(
                            taskcompletion__completion_date__range=(start_date, end_date),
                            taskcompletion__status='approved',
                            then=F('taskcompletion__task__points') + F('taskcompletion__bonus_points')
                        ),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                )
            ).order_by('-total_points')
        else:
            today = timezone.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if timezone.is_naive(start_of_month):
                start_of_month = timezone.make_aware(start_of_month)
            qs = Child.objects.annotate(
                total_points=Sum(
                    Case(
                        When(
                            taskcompletion__status='approved',
                            taskcompletion__completion_date__gte=start_of_month,
                            then=F('taskcompletion__task__points') + F('taskcompletion__bonus_points')
                        ),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                )
            ).order_by('-total_points')
        
        if city and city != "ALL":
            qs = qs.filter(city=city)
        if limit:
            qs = qs[:limit]
        return qs
    
    
    @staticmethod
    def update_child_streak(child: Child):
        """
        Updates the child's daily streak progress if they haven't checked in today.
        
        If the child's last streak date was yesterday, the streak continues.
        If the last streak date was more than a day ago, the streak resets.
        
        :param child: The Child instance to update.
        :return: The updated streak count.
        """
        today = date.today()

        if child.last_streak_date == today:
            return child.streak_count  

        # Update streak logic
        if child.last_streak_date == today - timedelta(days=1):
            child.streak_count += 1  # Continue streak
        else:
            child.streak_count = 1  # Reset streak

        child.last_streak_date = today
        child.save()

        return child.streak_count


    @staticmethod
    def get_current_streak(child: Child):
        """
        Retrieves the child's correct streak count based on the last recorded date.

        - If the last streak date is today → return current streak count.
        - If the last streak date was yesterday → return existing streak count.
        - If the last streak date was more than 1 day ago → streak resets to 0.

        :param child: The Child instance.
        :return: The correct streak count.
        """
        today = date.today()

        if child.last_streak_date == today:
            return child.streak_count  # Streak remains unchanged
        
        if child.last_streak_date == today - timedelta(days=1):
            return child.streak_count  # Continue streak
        
        child.streak_count = 0
        child.save()
        return 0  # Reset streak (more than 1 day gap)