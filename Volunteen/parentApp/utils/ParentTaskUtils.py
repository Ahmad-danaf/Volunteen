from teenApp.utils.TaskManagerUtils import TaskManagerUtils
from parentApp.models import Parent
from teenApp.entities.TaskAssignment import TaskAssignment
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion
from datetime import datetime
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
    
    
    @staticmethod
    def create_and_assign_task(parent: Parent, name: str, description: str, points: int, due_date: str, selected_children: list):
        """
        Create a new Task and assign it to each selected child.
        The parent's available teencoins are checked against the task's cost (points).
        If the parent's balance is insufficient, a ValueError is raised.
        Upon successful creation, the task is assigned to each valid child,
        and the parent's available teencoins are reduced accordingly.
        Returns the created Task and a list of its TaskAssignment objects.
        """
        if parent.available_teencoins < points:
            raise ValueError("Insufficient teencoins to assign this task.")
        if due_date and isinstance(due_date, str):
            converted_due_date = datetime.strptime(due_date, '%Y-%m-%d')
        else:
            converted_due_date = due_date
        # Create the task instance.
        task = Task.objects.create(
            title=name,
            description=description,
            points=points,
            deadline=converted_due_date,
        )
        assignments = []
        for child_id in selected_children:
            try:
                child = parent.children.get(id=child_id)
            except Child.DoesNotExist:
                continue  # Skip if child is not related to the parent.
            assignment = ParentTaskUtils.assign_task_to_child(parent, task, child)
            assignments.append(assignment)
        
        # Deduct the task cost from the parent's available teencoins.
        total_cost = points * len(selected_children)
        parent.available_teencoins -= max(0, total_cost)
        parent.save()
        
        return task, assignments
    
    
    @staticmethod
    def get_assigned_tasks_count(child):
        """
        Retrieve the count of tasks assigned to the child by the parent.
        Only count TaskAssignment records where the 'assigned_by' field matches the child's parent user.
        """
        if not child.parent:
            return 0
        return TaskAssignment.objects.filter(
            child=child, 
            assigned_by=child.parent.user
        ).count()

    @staticmethod
    def get_completed_tasks_count(child):
        """
        Retrieve the count of tasks completed by the child that were assigned by the parent.
        Only count TaskCompletion records with status 'approved' and where the related TaskAssignment's 'assigned_by'
        matches the child's parent user.
        """
        if not child.parent:
            return 0
        return TaskCompletion.objects.filter(
            child=child, 
            status="approved", 
            task__assignments__assigned_by=child.parent.user
        ).distinct().count()
