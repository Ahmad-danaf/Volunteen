from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion

class ChildTaskManager:

    @staticmethod
    def get_all_tasks(child):
        """
        Retrieve all tasks assigned to a child.
        This is based on TaskAssignment instead of Task to ensure correct filtering.
        """
        return TaskAssignment.objects.filter(child=child).values_list("task", flat=True)

    @staticmethod
    def get_assigned_tasks(child):
        """
        Retrieve all tasks assigned to a child that have not been completed.
        """
        return TaskAssignment.objects.filter(child=child)
    
    @staticmethod
    def get_all_child_active_tasks(child):
        """
        Retrieve all Task objects assigned to a child that have not been completed.
        Includes the `is_new` field from `TaskAssignment` and `status` from `TaskCompletion`.
        """
        from django.db.models import F, Subquery, OuterRef  # Needed for annotation

        # Retrieve only the task IDs that were completed
        completed_task_ids = TaskCompletion.objects.filter(
            child=child, status="approved"
        ).values_list("task_id", flat=True)

        # Subquery to fetch the latest status of the task for the child
        latest_status_subquery = TaskCompletion.objects.filter(
            task=OuterRef("pk"), child=child
        ).values("status")[:1]

        # Retrieve active tasks with `is_new` from TaskAssignment and `status` from TaskCompletion
        return Task.objects.filter(
            assignments__child=child, deadline__gte=timezone.now().date()
        ).exclude(id__in=completed_task_ids).annotate(
            is_new=F("assignments__is_new"),  # Fetching `is_new` field from TaskAssignment
            status=Subquery(latest_status_subquery)  # Fetching latest `status` from TaskCompletion
        ).distinct()

    @staticmethod
    def get_completed_tasks(child):
        """
        Retrieve all TaskCompletion records for tasks the child has completed and were approved.
        """
        return TaskCompletion.objects.filter(child=child, status="approved").select_related("task")

    @staticmethod
    def get_pending_tasks(child):
        """
        Retrieve tasks that are assigned but not yet completed.
        Now directly fetching from TaskCompletion where status is 'pending'.
        """
        return TaskCompletion.objects.filter(child=child, status="pending").values_list("task", flat=True)

    @staticmethod
    def get_overdue_tasks(child):
        """
        Retrieve overdue tasks assigned to the child that were not completed.
        """
        today = timezone.now().date()
        return TaskAssignment.objects.filter(child=child, task__deadline__lt=today).exclude(
            task__in=ChildTaskManager.get_completed_tasks(child)
        )

    @staticmethod
    def get_recently_completed_tasks(child, days=7):
        """
        Retrieve tasks the child completed and were approved within the last `days` days.
        """
        recent_date = timezone.now() - timedelta(days=days)
        return TaskCompletion.objects.filter(child=child, status="approved", completion_date__gte=recent_date)

    @staticmethod
    def mark_task_as_new(child, task):
        """
        Mark a task as new for a specific child.
        """
        task_assignment = TaskAssignment.objects.filter(task=task, child=child).first()

        if not task_assignment:
            raise ValidationError("Task assignment not found for this child.")

        task_assignment.is_new = True
        task_assignment.save()
        return True

    @staticmethod
    def mark_task_as_viewed(child, task):
        """
        Mark a task as viewed (not new) for a specific child.
        """
        task_assignment = TaskAssignment.objects.filter(task=task, child=child).first()

        if not task_assignment:
            raise ValidationError("Task assignment not found for this child.")

        task_assignment.is_new = False
        task_assignment.save()
        return True

    @staticmethod
    def get_tasks_by_status(child, status_filter):
        """
        Retrieve tasks filtered by status ('completed', 'pending', 'all').
        """
        if status_filter == 'completed':
            return ChildTaskManager.get_completed_tasks(child)
        elif status_filter == 'pending':
            return ChildTaskManager.get_pending_tasks(child)
        return ChildTaskManager.get_all_tasks(child)

    @staticmethod
    def get_tasks_by_date_filter(child, date_filter):
        """
        Retrieve tasks filtered by date ('today', 'this_week', 'this_month', 'all').
        """
        today = timezone.now().date()
        tasks = ChildTaskManager.get_all_tasks(child)

        if date_filter == 'today':
            return tasks.filter(completed_date__date=today)
        elif date_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            return tasks.filter(completed_date__date__gte=start_of_week)
        elif date_filter == 'this_month':
            return tasks.filter(completed_date__month=today.month)

        return tasks

    @staticmethod
    def get_filtered_tasks_by_status_date(child, status_filter, date_filter):
        """
        Retrieve tasks based on both status and date filters.
        """
        tasks = ChildTaskManager.get_tasks_by_status(child, status_filter)
        return ChildTaskManager.get_tasks_by_date_filter(child, date_filter).filter(id__in=tasks)

    @staticmethod
    def get_assigned_tasks_count(child):
        """
        Retrieve the count of tasks assigned to the child.
        """
        return TaskAssignment.objects.filter(child=child).count()

    @staticmethod
    def get_completed_tasks_count(child):
        """
        Retrieve the count of tasks completed by the child.
        """
        return TaskCompletion.objects.filter(child=child, status="approved").count()

    @staticmethod
    def get_total_tasks_count(child):
        """
        Retrieve the total count of tasks assigned to the child.
        """
        return TaskAssignment.objects.filter(child=child).count()

    @staticmethod
    def get_new_assigned_tasks_count(child):
        """
        Retrieve the count of new tasks assigned to the child.
        """
        return TaskAssignment.objects.filter(child=child, is_new=True).count()
    
    @staticmethod
    def get_new_assigned_tasks(child):
        """
        Retrieve the list of new tasks assigned to the child.
        """
        return TaskAssignment.objects.filter(child=child, is_new=True)