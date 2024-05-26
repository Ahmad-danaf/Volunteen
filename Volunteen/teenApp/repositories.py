from .models import Task, Child, Mentor

class TaskRepository:
    @staticmethod
    def get_tasks_by_mentor(mentor):
        return Task.objects.filter(assigned_mentors=mentor)
    
    @staticmethod
    def get_tasks_by_child(child):
        return Task.objects.filter(assigned_children=child)
    
    @staticmethod
    def get_all_tasks():
        return Task.objects.all()
    
    @staticmethod
    def get_task_by_id(task_id):
        return Task.objects.get(id=task_id)
    
    @staticmethod
    def get_completed_tasks_by_mentor(mentor):
        return Task.objects.filter(assigned_mentors=mentor, completed=True)

from .models import Child

class ChildRepository:
    @staticmethod
    def get_child_by_identifier(identifier):
        try:
            return Child.objects.get(identifier=identifier)
        except Child.DoesNotExist:
            raise Child.DoesNotExist(f"Child with identifier {identifier} does not exist.")
