from django.utils import timezone
from .models import Child, Task

def assign_points_to_children(identifiers, task):
    # Assign points to children based on task
    for identifier in identifiers:
        try:
            child = Child.objects.get(identifier=identifier)
            child.add_points(task.points)
            child.completed_tasks.add(task)
        except Child.DoesNotExist:
            print(f"Child with identifier {identifier} does not exist.")

def assign_task_to_children(task:Task, children_identifiers):
    for identifier in children_identifiers:
        try:
            child = Child.objects.get(identifier=identifier)
            
            task.assigned_children.add(child)
        except Child.DoesNotExist:
            print(f"Child with identifier {identifier} does not exist.")
    child.save()
    task.save() 
def check_and_mark_overdue_tasks(tasks):
    # Check and mark overdue tasks as completed
    for task in tasks:
        if task.is_overdue():
            task.completed = True
            task.save()

def assign_bonus_points(task, child, bonus_points):
    # Add bonus points to a child for a specific task
    child.points += bonus_points
    child.save()
    child.completed_tasks.add(task)
