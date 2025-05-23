from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import Task
from childApp.models import Child
from parentApp.models import Parent
from django.utils import timezone

DEFAULT_INCREASE_LEVEL_TASK = {
    'title': 'עלייה ברמה',
    'description': 'קיבלת נקודות מספיקות כדי לעלות רמה! המשך כך!',
    'points': 5,
    'img': 'defaults/LevelUp_Badge_Volunteen.jpg',
    'deadline': '2025-03-01',
}

DEFAULT_STREAK_MILESTONE_TASK = {
    "title": "🎯 בונוס התמדה",
    "description": "כל הכבוד! הגעת לרצף של {streak_day} ימים וקיבלת תגמול!",
    "points": 2,
    "img": "defaults/no-image.png",
    "deadline": '2025-03-01',  
}
class TaskManagerUtils:
    @staticmethod
    def get_assigned_tasks(user):
        """
        Retrieve TaskAssignment objects where the task was assigned by the given user.
        """
        return TaskAssignment.objects.filter(assigned_by=user)
    
    @staticmethod
    def assign_task(user, task: Task, child: Child):
        """
        Create a TaskAssignment for the given task and child,
        with the assigner set as the provided user.
        """
        assignment = TaskAssignment.objects.create(
            task=task,
            child=child,
            assigned_by=user
        )
        return assignment

    @staticmethod
    def approve_task_completion(user, task_completion: TaskCompletion):
        """
        Approve a task completion.
        
        This sets the status to 'approved', assigns the approver,
        calculates remaining_coins as task.points + bonus_points,
        awards the total points (task points plus bonus) to the child,
        and saves the completion record.
        
        Raises:
            ValueError: If the task completion is not in a pending state.
        """
        if task_completion.status=='approved':
            raise ValueError("Task completion is already approved.")
        
        task_completion.status = 'approved'
        task_completion.approved_by = user
        # Calculate remaining coins as the sum of the task's points and bonus points
        task_completion.remaining_coins = task_completion.task.points + task_completion.bonus_points
        task_completion.save()
        
        # Award points to the child
        task_completion.child.add_points(task_completion.task.points + task_completion.bonus_points)
        return task_completion
    
    @staticmethod
    def reject_task_completion(user, task_completion: TaskCompletion, feedback: str = None):
        """
        Reject a task completion.
        
        This sets the status to 'rejected', optionally records feedback,
        and saves the record.
        
        Raises:
            ValueError: If the task completion is not in a pending state.
        """
        if task_completion.status == 'rejected':
            raise ValueError("Task completion is already rejected.")
        
        task_completion.status = 'rejected'
        task_completion.mentor_feedback = feedback
        task_completion.save()
        return task_completion
    
    @staticmethod
    def get_or_create_increase_level_task(level):
        """
        Retrieves or creates the default 'increase level' task.
        """
        
        task, created = Task.objects.get_or_create(
            title=DEFAULT_INCREASE_LEVEL_TASK['title'] + " " + " | שלב " + str(level),
            defaults={
                'description': f"{DEFAULT_INCREASE_LEVEL_TASK['description']} (Level {level})",
                'points': DEFAULT_INCREASE_LEVEL_TASK['points'],
                'img': DEFAULT_INCREASE_LEVEL_TASK['img'],
                'deadline': DEFAULT_INCREASE_LEVEL_TASK['deadline'],
            }
        )
        return task

    @staticmethod
    def auto_approve_increase_level_for_child(child,level):
        """
        Automatically assigns and approves the default 'increase level' task for the child.
        Awards teencoins as per the task's configuration.
        """
        # Retrieve the default task.
        task = TaskManagerUtils.get_or_create_increase_level_task(level)
        
        # Create a task completion record for the child.
        task_completion, created = TaskCompletion.objects.get_or_create(
            task=task,
            child=child,
        )
        if created:
            TaskManagerUtils.assign_task(user=None, task=task, child=child)
            
        if task_completion.status != 'approved':
            # We pass None as user since no mentor/parent approving (system action)
            approved_completion = TaskManagerUtils.approve_task_completion(user=None, task_completion=task_completion)
            return approved_completion
            
        return task_completion
    
    @staticmethod
    def refund_task_assignment(assignment, owner):
        """
        Refund a task assignment for the given owner (parent or mentor).
        
        Args:
            assignment (TaskAssignment): The assignment to refund.
            owner (Parent or Mentor): The owner who assigned the task.
        
        Raises:
            ValueError: If the assignment has been refunded already or
                        if the child has already started the task (i.e. TaskCompletion exists).
                        
        Returns:
            TaskAssignment: The updated assignment.
        """
        if assignment.refunded_at is not None:
            raise ValueError("Task assignment has already been refunded.")
        
        if TaskCompletion.objects.filter(task=assignment.task, child=assignment.child).exists():
            raise ValueError("Task already started; refund not allowed.")
        
        assignment.refunded_at = timezone.now()
        assignment.save()
        
        # Refund the task points to the owner
        owner.available_teencoins += assignment.task.points
        owner.save()
        
        return assignment


    @staticmethod
    def get_or_create_streak_milestone_task(streak_day):
        """
        Retrieves or creates the default milestone reward task for the given streak day.
        """
        title = f"{DEFAULT_STREAK_MILESTONE_TASK['title']} | יום {streak_day}"

        task, created = Task.objects.get_or_create(
            title=title,
            defaults={
                'description': DEFAULT_STREAK_MILESTONE_TASK['description'].format(streak_day=streak_day),
                'points': DEFAULT_STREAK_MILESTONE_TASK['points'],
                'img': DEFAULT_STREAK_MILESTONE_TASK['img'],
                'deadline': DEFAULT_STREAK_MILESTONE_TASK['deadline'],
            }
        )
        return task
    
    @staticmethod
    def auto_approve_streak_milestone_for_child(child, streak_day):
        """
        Automatically assigns and approves a milestone reward task to the child.
        Used when a child hits a streak milestone like 10, 20, 30 days.
        """
        task = TaskManagerUtils.get_or_create_streak_milestone_task(streak_day)

        task_completion, created = TaskCompletion.objects.get_or_create(
            task=task,
            child=child,
        )
        if created:
            TaskManagerUtils.assign_task(user=None, task=task, child=child)

        if task_completion.status != 'approved':
            return TaskManagerUtils.approve_task_completion(user=None, task_completion=task_completion)

        return task_completion