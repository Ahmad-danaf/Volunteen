from teenApp.utils.TaskManagerUtils import TaskManagerUtils
from parentApp.models import Parent
from teenApp.entities.TaskAssignment import TaskAssignment
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion

class ParentTaskUtils(TaskManagerUtils):
    @staticmethod
    def get_children(parent: Parent):
        """
        Return a queryset of children belonging to the given parent.
        """
        return parent.children.all()
    
    @staticmethod
    def get_tasks_assigned_by_parent(parent: Parent):
        """
        Retrieve TaskAssignment objects for tasks assigned by the parent.
        """
        return TaskAssignment.objects.filter(assigned_by=parent.user)
    
    @staticmethod
    def get_tasks_assigned_by_mentors_for_parent_children(parent: Parent):
        """
        Retrieve TaskAssignment objects for the parent's children that were not
        assigned by the parent (e.g. those assigned by mentors).
        """
        return TaskAssignment.objects.filter(child__in=parent.children.all()).exclude(assigned_by=parent.user)
    
    @staticmethod
    def assign_task_to_child(parent: Parent, task: Task, child: Child):
        """
        Assign a task to a child from the parent's account.
        
        Validates that the child belongs to the parent and then calls the shared 
        assign_task logic.
        
        Raises:
            ValueError: If the child does not belong to the parent.
        """
        if child.parent != parent:
            raise ValueError("This child does not belong to the current parent.")
        
        return ParentTaskUtils.assign_task(parent.user, task, child)