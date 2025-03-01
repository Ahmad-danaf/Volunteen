from django.db.models import Sum, Case, When, Value, IntegerField, F
from django.utils import timezone
from childApp.models import Child
from teenApp.entities.TaskCompletion import TaskCompletion
from .child_level_management import calculate_total_points  
from datetime import datetime, time

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
