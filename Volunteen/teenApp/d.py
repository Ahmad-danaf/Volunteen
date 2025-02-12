from teenApp.entities.task import Task
from django.db import transaction

def duplicate_last_task():
    """
    Duplicates the last task in the database, including:
    - Title (marked as a copy)
    - Assigned children (ManyToManyField)
    - Assigned mentors (ManyToManyField)
    """
    # Get the last created task (assuming ordering by ID)
    last_task = Task.objects.order_by('-id').first()

    if last_task:
        # Copy all field values except ID
        task_data = Task.objects.filter(id=last_task.id).values().first()
        task_data.pop("id")  # Remove primary key

        with transaction.atomic():  # Ensure all copies are done safely
            # Create a new task with the same data
            new_task = Task.objects.create(**task_data)
            new_task.title = last_task.title + " (Copy)"  # Mark as a copy
            new_task.completed = False  # Reset completion status
            new_task.save()

            # Copy ManyToMany relationships (assigned children & mentors)
            new_task.assigned_children.set(last_task.assigned_children.all())
            new_task.assigned_mentors.set(last_task.assigned_mentors.all())

        print(f"Task duplicated successfully! New Task ID: {new_task.id}")
        return new_task
    else:
        print("No tasks found in the database.")
        return None

def d(times=5):
    for _ in range(times):
        duplicate_last_task()
