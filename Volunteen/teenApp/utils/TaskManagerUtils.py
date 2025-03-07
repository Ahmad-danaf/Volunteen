from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import Task
from childApp.models import Child
from parentApp.models import Parent

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
        if task_completion.status != 'pending':
            raise ValueError("Task completion is not in a pending state.")
        
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
        if task_completion.status != 'pending':
            raise ValueError("Task completion is not in a pending state.")
        
        task_completion.status = 'rejected'
        # Reusing mentor_feedback field for feedback; can be renamed if a more generic name is needed.
        task_completion.mentor_feedback = feedback
        task_completion.save()
        return task_completion