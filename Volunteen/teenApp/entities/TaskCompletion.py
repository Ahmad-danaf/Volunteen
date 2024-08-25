from django.db import models
from django.utils import timezone

class TaskCompletion(models.Model):
    child = models.ForeignKey('Child', on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    completion_date = models.DateTimeField(default=timezone.now)
    bonus_points= models.IntegerField(default=0)

    class Meta:
        unique_together = ('child', 'task')  # Ensure that each child can only complete a task once

    def __str__(self):
        return f"{self.child.user.username} completed {self.task.title} on {self.completion_date}"