from django.db.models import Sum, Case, When, Value, IntegerField, F,Q
from django.db.models.functions import Coalesce
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
        return start_datetime, end_datetime
    
    
    @staticmethod
    def get_donations_leaderboard(start_date=None, end_date=None, limit=None, city="ALL", institution=None):
        """
        Returns a queryset of top donors based on DonationTransaction amounts.
        
        If start_date and end_date are provided, the leaderboard is calculated over that date range.
        Otherwise, it defaults to using the current month (from the 1st day until now).
        
        Each entry contains the child's id, username, city, and total donated amount.
        If a city is provided (other than "ALL"), the leaderboard is filtered by that city.
        If an institution is provided, the leaderboard is filtered to show only children from that institution.
        """
        now = timezone.now()
        if not start_date or not end_date:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        
        # Ensure dates are timezone-aware
        start_datetime, end_datetime = LeaderboardUtils.convert_dates_to_datetime_range(start_date, end_date)
        
        qs = (DonationTransaction.objects
          .filter(date_donated__range=(start_datetime, end_datetime))
          .values('child__id', 'child__user__username', 'child__city')
          .annotate(total_donated=Sum('amount'))
          .order_by('-total_donated'))
    
        if city and city != "ALL":
            qs = qs.filter(child__city=city)
        
        if limit:
            qs = qs[:limit]
            
        if institution:
            qs = qs.filter(child__institution=institution)
            
        return qs
    
    
    @staticmethod
    def get_children_leaderboard(start_date=None, end_date=None, institution=None, city=None, limit=None):
        """
        Returns a queryset of Child objects annotated with total points from approved tasks,
        optionally filtered by institution, city, and a custom intuition value.

        - If start_date and end_date are provided, it calculates points earned within that range.
        - Otherwise, it defaults to using the current month (from the 1st day until now).
        - Optionally filters by a given institution (if provided and not "ALL").
        - Additional filtering can be applied for city and intuition.
        - A limit (e.g., top 3) can be used to restrict the number of results.
        """
        # Start with all children, then filter early by institution if provided.
        qs = Child.objects.all()
        
        if institution:
            qs = qs.filter(institution=institution)
        
        if city and city != "ALL":
            qs = qs.filter(city=city)
        
        # Create the annotation for total points based on the provided date range.
        if start_date and end_date:
            date_q = Q(
            taskcompletion__completion_date__range=(start_date, end_date)
        )
        else:
            today = timezone.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if timezone.is_naive(start_of_month):
                start_of_month = timezone.make_aware(start_of_month)
            date_q = Q(
            taskcompletion__completion_date__gte=start_of_month
            )
        
        approved_q = Q(taskcompletion__status='approved')
        inst_q = Q()
        if institution:
            inst_q = Q(
                taskcompletion__task__assigned_mentors__institutions=institution
            )
        qs = qs.annotate(
            total_points=Coalesce(
                Sum(
                    F('taskcompletion__task__points') + F('taskcompletion__bonus_points'),
                    filter=(date_q & approved_q & inst_q),
                    output_field=IntegerField()
                ),
                Value(0),
                output_field=IntegerField()
            )
)
        
        # Order by total_points in descending order.
        qs = qs.order_by('-total_points')

        # Apply a limit to the queryset, if provided.
        if limit:
            qs = qs[:limit]
        
        return qs

    @staticmethod
    def _compute_rank_for_child(child, children_list):
        """
        Compute the rank of a given child from the provided sorted children_list based on total_points.
        """
        rank = 1
        prev_points = None

        for i, ch in enumerate(children_list, start=1):
            if i == 1:
                prev_points = ch.total_points
                if ch == child:
                    return rank
            else:
                if ch.total_points < prev_points:
                    rank = i
                prev_points = ch.total_points
                if ch == child:
                    return rank
        return None

    @staticmethod
    def _annotate_rank(children):
        """
        Annotate the provided list of children with a 'user_rank' attribute.
        """
        rank = 1
        prev_points = None

        for i, child in enumerate(children):
            if i == 0:
                child.user_rank = rank
                prev_points = child.total_points
            else:
                if child.total_points < prev_points:
                    rank = i + 1
                child.user_rank = rank
                prev_points = child.total_points
        return children

    @staticmethod
    def get_custom_leaderboard(child, start_date=None, end_date=None, institution=None, city=None, top_limit=10):
        """
        Returns a dictionary with keys:
        - 'top_children': list of top children (annotated with ranks)
        - 'extra_children': list of extra children (including the current child plus one above/below)
        - 'show_divider': boolean indicating if a visual divider is needed between the top list and extra list.
        """
        children_qs = LeaderboardUtils.get_children_leaderboard(start_date, end_date, institution, city)
        top_children = list(children_qs[:top_limit])
        top_children = LeaderboardUtils._annotate_rank(top_children)
        extra_children = []
        show_divider = False

        # If the current child is not in the top list.
        if child not in top_children:
            full_children_list = list(children_qs)
            child_rank = LeaderboardUtils._compute_rank_for_child(child, full_children_list)
            child_index = next((i for i, c in enumerate(full_children_list) if c == child), None)

            if child_index is not None:
                # Get one child above and one below the current child (if available).
                nearby = full_children_list[
                    max(0, child_index - 1) : min(child_index + 2, len(full_children_list))
                ]
                # Assign the nearby list to extra_children so it isn't empty.
                extra_children = nearby[:]
                for c in extra_children:
                    c.user_rank = LeaderboardUtils._compute_rank_for_child(c, full_children_list)
                    if c == child:
                        c.is_current_user = True
                            
                # Determine if there's a gap between the top block and the extra block.
                if extra_children and (extra_children[0].user_rank > top_limit + 1):
                    show_divider = True    
        else:
            # If the child is already in the top list, mark them as current.
            for c in top_children:
                if c == child:
                    c.is_current_user = True

        return {
            'top_children': top_children,
            'extra_children': extra_children,
            'show_divider': show_divider
        }
    
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
    
    
    @staticmethod
    def get_top_streaks(institution=None, limit=None):
        """
        Returns a queryset of Child objects ordered by their streak_count in descending order.
        
        Optionally filters by institution if provided (and not "ALL"), 
        and applies a limit (e.g. top 5, top 10).
        
        :param institution: An Institution instance or identifier to filter by.
        :param limit: Optional integer to limit the number of results.
        :return: QuerySet of Child objects.
        """
        qs=Child.objects.all()
        if institution and institution != "ALL":
            qs=qs.filter(institution=institution)
            
        qs=qs.order_by('-streak_count')
        if limit:
            qs=qs[:limit]
        return qs
