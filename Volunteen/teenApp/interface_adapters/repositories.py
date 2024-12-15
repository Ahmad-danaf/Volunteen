from teenApp.entities.task import Task
from childApp.models import Child
from mentorApp.models import Mentor

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

class ChildRepository:
    @staticmethod
    def get_child_by_identifier(identifier):
        try:
            return Child.objects.get(identifier=identifier)
        except Child.DoesNotExist:
            raise Child.DoesNotExist(f"Child with identifier {identifier} does not exist.")
    def get_child_by_id(self, child_id):
        return Child.objects.get(id=child_id)

class MentorRepository:
    def get_mentor_by_id(self, mentor_id):
        return Mentor.objects.get(id=mentor_id)