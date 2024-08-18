from teenApp.entities.task import Task
from teenApp.entities.child import Child
from teenApp.entities.TaskCompletion import TaskCompletion


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
                
                # Check if the child has already completed this task
                if TaskCompletion.objects.filter(child=child, task=task).exists():
                    errors.append(f"Child with identifier {identifier} has already completed this task.")
                else:
                    # Create a new TaskCompletion entry to record that the child completed the task
                    TaskCompletion.objects.create(child=child, task=task)
                    
                    # Add points to the child
                    child.add_points(task.points)
            except Child.DoesNotExist:
                errors.append(f"Child with identifier {identifier} does not exist.")

        if errors:
            raise ValueError(" ".join(errors))

        task.save()