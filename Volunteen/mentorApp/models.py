from django.db import models
from django.contrib.auth.models import User, Group
from teenApp.entities.TaskAssignment import TaskAssignment
from childApp.models import Child
from teenApp.entities import TaskCompletion

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

    def assign_task_to_children(task, children_identifiers):
   
        for identifier in children_identifiers:
            try:
                # שליפת ילד על פי המזהה
                child = Child.objects.get(identifier=identifier)

                # הוספת הילד לשדה assigned_children במשימה
                task.assigned_children.add(child)

                # סימון המשימה כ"חדשה" עבור הילד ב-TaskAssignment
                TaskAssignment.objects.get_or_create(task=task, child=child, defaults={'is_new': True})
            
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")


    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        mentors_group, created = Group.objects.get_or_create(name='Mentors')
        self.user.groups.add(mentors_group)

    def review_task(self, task, child, approve=True, feedback=None):
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