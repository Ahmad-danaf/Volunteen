from .repositories import TaskRepository, ChildRepository

from .models import Task, Child

from .repositories import TaskRepository, ChildRepository
from .repositories import ChildRepository, TaskRepository

from .repositories import TaskRepository, ChildRepository

class AssignPointsToChildren:
    def __init__(self, task_repo, child_repo):
        self.task_repo = task_repo
        self.child_repo = child_repo

    def execute(self, children_identifiers, task_id):
        task = self.task_repo.get_task_by_id(task_id)
        errors = []
        
        for identifier in children_identifiers:
            try:
                child = self.child_repo.get_child_by_identifier(identifier)
                child.add_points(task.points)
                task.completed_by.add(child)
            except Child.DoesNotExist:
                errors.append(f"Child with identifier {identifier} does not exist.")
        
        if errors:
            raise ValueError(" ".join(errors))
        task.save()

class AssignTaskToChildren:
    def __init__(self, child_repo):
        self.child_repo = child_repo

    def execute(self, task_id, children_identifiers):
        task = Task.objects.get(id=task_id)
        for identifier in children_identifiers:
            try:
                child = self.child_repo.get_child_by_identifier(identifier)
                print(f"Assigning task {task.title} to child {child.identifier}")
                task.assigned_children.add(child)
                task.new_task = True
            except Child.DoesNotExist:
                raise ValueError(f"Child with identifier {identifier} does not exist.")
        task.save()

        
class CheckAndMarkOverdueTasks:
    def __init__(self, task_repo):
        self.task_repo = task_repo

    def execute(self, mentor):
        tasks = self.task_repo.get_tasks_by_mentor(mentor)
        for task in tasks:
            if task.is_overdue():
                task.completed = True
                task.save()

class AssignBonusPoints:
    def __init__(self, task_repo, child_repo):
        self.task_repo = task_repo
        self.child_repo = child_repo

    def execute(self, task_id, child_id, bonus_points):
        task = self.task_repo.get_task_by_id(task_id)
        child = self.child_repo.get_child_by_identifier(child_id)
        child.add_points(bonus_points)
        task.completed_by.add(child)
        task.save()

assign_points_to_children = AssignPointsToChildren(TaskRepository, ChildRepository)
assign_task_to_children = AssignTaskToChildren(ChildRepository)
check_and_mark_overdue_tasks = CheckAndMarkOverdueTasks(TaskRepository)
assign_bonus_points = AssignBonusPoints(TaskRepository, ChildRepository)
