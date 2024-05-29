from teenApp.entities.task import Task
from teenApp.entities.child import Child

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
