from django.db import models

class TaskAssignment(models.Model):
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='assignments')
    child = models.ForeignKey('childApp.Child', on_delete=models.CASCADE, related_name='assignments')
    is_new = models.BooleanField(default=True, verbose_name="Is New", help_text="Indicates if the task is new for the child.")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")

    def __str__(self):
        return f"Task: {self.task.title}, Child: {self.child.user.username}"
