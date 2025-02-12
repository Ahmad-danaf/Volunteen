from datetime import timedelta
from django.utils import timezone
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from django.shortcuts import get_object_or_404

class ChildTaskManager:
    
    @staticmethod
    def get_all_tasks(child):
        """Retrieve all tasks assigned to a child."""
        return Task.objects.filter(assigned_children=child)

    @staticmethod
    # TaskAssignment- not pending + Task -assigned_children feild
    def get_assigned_tasks(child):
        """Retrieve all tasks assigned to a child."""
        return Task.objects.filter(assigned_children=child)

    @staticmethod
    def get_completed_tasks(child):
        """Retrieve all tasks the child has completed."""
        return TaskCompletion.objects.filter(child=child, status="approved").values_list("task", flat=True)

    @staticmethod
    def get_pending_tasks(child):
        # TaskAssignment that are not completed in TaskCompletion
        """Retrieve tasks that are assigned but not yet completed."""
        completed_task_ids = ChildTaskManager.get_completed_tasks(child)
        return Task.objects.filter(assigned_children=child).exclude(id__in=completed_task_ids)

    @staticmethod
    def get_overdue_tasks(child):
        # TaskAssignment that are not completed in TaskCompletion and date is less than today
        """Retrieve overdue tasks assigned to the child."""
        today = timezone.now().date()
        return Task.objects.filter(assigned_children=child, deadline__lt=today, completed=False)

    @staticmethod
    def get_recently_completed_tasks(child, days=7):
        """Retrieve tasks the child completed within the last `days` days."""
        recent_date = timezone.now() - timedelta(days=days)
        return TaskCompletion.objects.filter(child=child, status="approved", completion_date__gte=recent_date).values_list("task", flat=True)

    @staticmethod
    def approve_task_completion(child, task):
        """Approve a child's task completion and grant points."""
        task_completion, created = TaskCompletion.objects.get_or_create(task=task, child=child)
        if task_completion.status != "approved":
            task_completion.status = "approved"
            task_completion.remaining_coins = task.points + task_completion.bonus_points
            task_completion.save()
            child.add_points(task.points)  # Reward points
            return True
        return False  # Task was already approved

    @staticmethod
    def reject_task_completion(child, task, feedback=None):
        """Reject a child's task completion with optional feedback."""
        task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
        if task_completion and task_completion.status == "pending":
            task_completion.status = "rejected"
            task_completion.mentor_feedback = feedback
            task_completion.save()
            return True
        return False  # Task was not pending

    @staticmethod
    def mark_task_as_new(child, task):
        """Mark the task as new for a specific child."""
        task_assignment = TaskAssignment.objects.filter(task=task, child=child).first()
        if task_assignment:
            task_assignment.is_new = True
            task_assignment.save()
            return True
        return False  # Task assignment not found

    @staticmethod
    def mark_task_as_viewed(child, task):
        """Mark the task as viewed (not new) for a specific child."""
        task_assignment = TaskAssignment.objects.filter(task=task, child=child).first()
        if task_assignment:
            task_assignment.is_new = False
            task_assignment.save()
            return True
        return False  # Task assignment not found

    @staticmethod
    def get_expiring_teencoins(child, days=7):
        """Retrieve tasks with TeenCoins expiring soon (within `days` days)."""
        expiry_date = timezone.now() + timedelta(days=days)
        return TaskCompletion.objects.filter(child=child, status="approved", completion_date__lte=expiry_date).values_list("task", flat=True)

    @staticmethod
    def get_assigned_tasks_count(child):
        """Retrieve the count of tasks assigned to the child."""
        return TaskAssignment.objects.filter(child=child).count()
    
    @staticmethod
    def get_completed_tasks_count(child):
        """Retrieve the count of tasks completed by the child."""
        return TaskCompletion.objects.filter(child=child, status="approved").count()
    
    @staticmethod
    def get_total_tasks_count(child):
        """Retrieve the total count of tasks assigned to the child."""
        return Task.objects.filter(assigned_children=child).count()
    
    @staticmethod
    def get_tasks_by_status(child, status_filter):
        """Retrieve tasks filtered by status ('completed', 'pending', 'all')."""
        if status_filter == 'completed':
            return ChildTaskManager.get_completed_tasks(child)
        elif status_filter == 'pending':
            return ChildTaskManager.get_pending_tasks(child)
        return ChildTaskManager.get_all_tasks(child)  # Default: all tasks

    @staticmethod
    def get_tasks_by_date_filter(child, date_filter):
        """Retrieve tasks filtered by date ('today', 'this_week', 'this_month', 'all')."""
        if date_filter == 'all':
            return ChildTaskManager.get_all_tasks(child)

        today = timezone.now().date()
        tasks = ChildTaskManager.get_all_tasks(child)

        if date_filter == 'today':
            return tasks.filter(completed_date__date=today)
        elif date_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())  # Start of the current week (Monday)
            return tasks.filter(completed_date__date__gte=start_of_week)
        elif date_filter == 'this_month':
            return tasks.filter(completed_date__month=today.month)

        return tasks  # Default fallback

    @staticmethod
    def get_filtered_tasks_by_status_date(child, status_filter, date_filter):
        """Retrieve tasks based on both status and date filters."""
        tasks = ChildTaskManager.get_tasks_by_status(child, status_filter)
        return ChildTaskManager.get_tasks_by_date_filter(child, date_filter).filter(id__in=tasks)


    