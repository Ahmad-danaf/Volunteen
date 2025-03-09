from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.TaskAssignment import TaskAssignment
from mentorApp.forms import TaskForm
from teenApp.utils.TaskManagerUtils import TaskManagerUtils
from childApp.utils.child_task_manager import ChildTaskManager
from django.db.models import Q, Subquery, OuterRef

class MentorTaskUtils(TaskManagerUtils):
    
    
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
        tasks = MentorTaskUtils.get_mentor_tasks_by_status(child, status_filter)
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
        Retrieve the count of mentor-assigned tasks for the given child.
        A mentor-assigned task is defined as one that:
        - Has a TaskAssignment with an assigned_by user who is a mentor, or
        - Its Task has at least one assigned_mentor.
        """
        return TaskAssignment.objects.filter(child=child).filter(
            Q(assigned_by__mentor__isnull=False) | Q(task__assigned_mentors__isnull=False)
        ).distinct().count()

    @staticmethod
    def get_completed_tasks_count(child):
        """
        Retrieve the count of mentor-assigned tasks completed (approved) by the child.
        A mentor-assigned task is defined as one that:
        - Has a related TaskAssignment with an assigned_by user who is a mentor, or
        - Its Task has at least one assigned_mentor.
        """
        return TaskCompletion.objects.filter(child=child, status="approved").filter(
            Q(task__assignments__assigned_by__mentor__isnull=False) | Q(task__assigned_mentors__isnull=False)
        ).distinct().count()





        
