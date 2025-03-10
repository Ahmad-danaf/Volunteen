from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from django.db.models import Subquery, OuterRef, F, Value, CharField

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
        return TaskCompletion.objects.filter(child=child, status="approved")

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
        Return a queryset of Task objects filtered by 'completed', 'pending', or 'all'.
        """
        assigned_tasks_ids = TaskAssignment.objects.filter(child=child).values_list("task_id", flat=True)
        tasks = Task.objects.filter(id__in=assigned_tasks_ids)
        completed_tasks_ids = TaskCompletion.objects.filter(child=child, status="approved").values_list("task_id", flat=True)

        if status_filter == 'completed':
            return tasks.filter(id__in=completed_tasks_ids)
        elif status_filter == 'pending':
            return tasks.exclude(id__in=completed_tasks_ids)
        return tasks  # 'all'

    @staticmethod
    def get_tasks_by_date_filter(tasks, date_filter):
        """
        Filter a queryset of Task objects by date based on their 'deadline'.
        """
        today = timezone.now().date()
        if date_filter == 'today':
            return tasks.filter(deadline=today)
        elif date_filter == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return tasks.filter(deadline__range=[start_of_week, end_of_week])
        elif date_filter == 'this_month':
            return tasks.filter(deadline__year=today.year, deadline__month=today.month)
        return tasks

    @staticmethod
    def get_filtered_tasks_by_status_date(child, status_filter, date_filter):
        """
        Combine status and date filters to return Task objects.
        """
        tasks = ChildTaskManager.get_tasks_by_status(child, status_filter)
        tasks = tasks.annotate(
            completion_date=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('completion_date')[:1]
            ),
            completion_status=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('status')[:1]
            ),
            mentor_feedback=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('mentor_feedback')[:1]
            )
        )
        return ChildTaskManager.get_tasks_by_date_filter(tasks, date_filter)

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
    
    
    @staticmethod
    def get_unresolved_tasks_for_child(child):
        """
        Returns all tasks assigned to a child that are either:
        - Not in TaskCompletion at all.
        - In TaskCompletion but not approved or rejected.
        Also includes the status from TaskCompletion (if exists).
        """
        # Get tasks assigned to the child
        assigned_task_ids = TaskAssignment.objects.filter(child=child).values_list('task_id', flat=True)

        # Get tasks that are either approved or rejected
        excluded_task_ids = TaskCompletion.objects.filter(
            child=child, status__in=['approved', 'rejected']
        ).values_list('task_id', flat=True)

        # Subquery to fetch the latest status of the task for the child
        latest_status_subquery = TaskCompletion.objects.filter(
            task=OuterRef("pk"), child=child
        ).values("status")[:1]  # Fetch only one latest status

        # Filter tasks: Assigned to the child but not approved or rejected
        unapproved_tasks = Task.objects.filter(
            id__in=assigned_task_ids
        ).exclude(id__in=excluded_task_ids).annotate(
            status=Subquery(latest_status_subquery, output_field=CharField())  # Attach status
        )

        return unapproved_tasks
    
    
    
    @staticmethod
    def get_mentor_tasks_by_status(child, status_filter):
        """
        Return a queryset of Task objects that are mentor-assigned for the given child,
        filtered by 'completed', 'pending', or 'all'.

        A mentor-assigned task is defined as one that meets at least one of the following:
        - Its TaskAssignment has a non-null assigned_by field where the user is a mentor.
        - Its Task has a non-empty assigned_mentors field.
        """
        # Get IDs of tasks assigned to the child by a mentor, or tasks that have assigned_mentors.
        mentor_assigned_tasks_ids = TaskAssignment.objects.filter(child=child).filter(
            Q(assigned_by__mentor__isnull=False) | Q(task__assigned_mentors__isnull=False)
        ).values_list("task_id", flat=True)

        tasks = Task.objects.filter(id__in=mentor_assigned_tasks_ids)
        completed_tasks_ids = TaskCompletion.objects.filter(child=child, status="approved").values_list("task_id", flat=True)

        if status_filter == "completed":
            return tasks.filter(id__in=completed_tasks_ids)
        elif status_filter == "pending":
            return tasks.exclude(id__in=completed_tasks_ids)
        return tasks  # For 'all'
    
    @staticmethod
    def get_mentor_tasks_by_status_date(child, status_filter, date_filter):
        """
        Combine status and date filters to return Task objects.
        """
        tasks = ChildTaskManager.get_mentor_tasks_by_status(child, status_filter)
        tasks = tasks.annotate(
            completion_date=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('completion_date')[:1]
            ),
            completion_status=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('status')[:1]
            ),
            mentor_feedback=Subquery(
                TaskCompletion.objects.filter(
                    child=child, task=OuterRef('pk')
                ).values('mentor_feedback')[:1]
            )
        )
        return ChildTaskManager.get_tasks_by_date_filter(tasks, date_filter)
    
    
    @staticmethod
    def get_mentor_assigned_tasks_count(child):
        """
        Retrieve the count of mentor-assigned tasks for the given child.
        A mentor-assigned task is defined as one that:
        - Has a TaskAssignment with an assigned_by user who is a mentor, or
        - Its Task has at least one assigned_mentor.
        """
        return TaskAssignment.objects.filter(child=child).filter(
            Q(assigned_by__mentor__isnull=False) | Q(task__assigned_mentors__isnull=False)
        ).distinct().count()

    @staticmethod
    def get_mentor_completed_tasks_count(child):
        """
        Retrieve the count of mentor-assigned tasks completed (approved) by the child.
        A mentor-assigned task is defined as one that:
        - Has a related TaskAssignment with an assigned_by user who is a mentor, or
        - Its Task has at least one assigned_mentor.
        """
        return TaskCompletion.objects.filter(child=child, status="approved").filter(
            Q(task__assignments__assigned_by__mentor__isnull=False) | Q(task__assigned_mentors__isnull=False)
        ).distinct().count()
    
    
 