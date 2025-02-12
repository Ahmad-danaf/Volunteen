from django.db import models
from django.contrib.auth.models import User, Group
from childApp.models import Child
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import Task
class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Mentor User")

    # Available Teencoins for the mentor (balance for assigning tasks)
    available_teencoins = models.IntegerField(default=0, verbose_name="Available Teencoins")

    def __str__(self):
        return self.user.username

    def assign_task_to_children(self, task, children_identifiers):
        """
        Assigns a task to multiple children.
        Ensures that the task is linked properly and marked as 'new' for the children.
        """
        for identifier in children_identifiers:
            try:
                child = Child.objects.get(identifier=identifier)
                task.assigned_children.add(child)  # Linking child to task
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")
        
        task.save()  # Ensure task is updated after modifications


    def assign_teencoins_to_task(self, task, amount):
        """
        Allocates Teencoins from the mentor's balance to a task.
        Ensures that the allocation does not exceed the available balance.
        """
        if amount > self.available_teencoins:
            raise ValueError("Not enough available Teencoins.")
        
        task.points = amount
        self.available_teencoins -= amount
        task.save()
        self.save()

    def get_assigned_teencoins(self):
        """
        Returns the total Teencoins allocated by this mentor but not yet approved.
        """
        return Task.objects.filter(assigned_mentors=self).aggregate(models.Sum('points'))['points__sum'] or 0

    def get_transferred_teencoins(self):
        """
        Returns the total Teencoins that have been approved and transferred to children.
        """
        return TaskCompletion.objects.filter(
            task__assigned_mentors=self, status='approved'
        ).aggregate(models.Sum('task__points'))['task__points__sum'] or 0

    def review_task(self, task, child, approve=True, feedback=None):
        """
        Reviews a task completion request.
        If approved, the child receives the assigned Teencoins.
        """
        task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
        if task_completion:
            if approve:
                task_completion.status = 'approved'
                task_completion.save()
                child.add_points(task.points)
            else:
                task_completion.status = 'rejected'
                task_completion.mentor_feedback = feedback
                task_completion.save()

    def save(self, *args, **kwargs):
        """
        Automatically assigns the mentor to the 'Mentors' group if not already added.
        """
        super().save(*args, **kwargs)
        mentors_group, created = Group.objects.get_or_create(name='Mentors')
        self.user.groups.add(mentors_group)
