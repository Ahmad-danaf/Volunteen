from teenApp.entities.task import Task
from teenApp.entities.child import Child

class AssignTaskToChildren:
    def __init__(self, child_repo):
        self.child_repo = child_repo

    def execute(self, task_id, children_identifiers):
        task = Task.objects.get(id=task_id)
        for identifier in children_identifiers:
            try:
                child = self.child_repo.get_child_by_identifier(identifier)
                task.assigned_children.add(child)
                task.new_task = True
            except Child.DoesNotExist:
                raise ValueError(f"Child with identifier {identifier} does not exist.")
        task.save()
