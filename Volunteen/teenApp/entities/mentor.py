from django.db import models
from django.contrib.auth.models import User, Group
from teenApp.entities.child import Child

class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def assign_points_to_children(self, identifiers, task):
        for identifier in identifiers:
            try:
                child = Child.objects.get(identifier=identifier)
                child.add_points(task.points)
                child.completed_tasks.add(task)
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")

    def assign_task_to_children(self, task, children_identifiers):
        for identifier in children_identifiers:
            try:
                child = Child.objects.get(identifier=identifier)
                task.assigned_children.add(child)
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        mentors_group, created = Group.objects.get_or_create(name='Mentors')
        self.user.groups.add(mentors_group)
