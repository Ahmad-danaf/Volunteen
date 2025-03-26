from django.db.models import Q
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils
class MentorUtils:
    
    @staticmethod
    def get_children_for_mentor(mentor, search_query=''):
        """
        Return all Children belonging to a given mentor, optionally filtered by a search query.
        The search query will match username, first_name, or last_name.
        """
        children = mentor.children.all()
        if search_query:
            children = children.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )
        return children
    
    @staticmethod
    def get_children_performance_data(mentor):
        """
        Returns a list of performance data dictionaries for each child of the mentor.
        Each dictionary contains the child's name, number of tasks assigned by the mentor,
        and number of approved task completions.
        """
        performance_data = []
        children = mentor.children.all()

        for child in children:
            approved_completions = MentorTaskUtils.count_approved_task_completions_for_child_from_mentor(
                mentor, child
            )
            total_assigned_tasks = MentorTaskUtils.count_total_assigned_tasks_for_child_from_mentor(
                mentor, child
            )
            total_active_tasks = MentorTaskUtils.get_active_tasks_for_child_from_mentor(mentor, child).count()
            missing_tasks = max(total_assigned_tasks - approved_completions - total_active_tasks, 0)
            non_active_tasks = total_assigned_tasks - total_active_tasks
            if non_active_tasks > 0:
                efficiency = round((approved_completions / non_active_tasks) * 100, 2)
            else:
                efficiency = 0.0
            performance_data.append({
                'child_id': child.id,
                'child_name': child.user.username,
                'approved_completions': approved_completions,
                'total_assigned_tasks': total_assigned_tasks,
                'total_active_tasks': total_active_tasks,
                'missing_tasks': missing_tasks,
                'efficiency_percent': efficiency,
                'non_active_tasks': non_active_tasks,
            })

        return performance_data
