from django.db import models

# Create your models here.

from django.db import models

class Task(models.Model):
    description = models.TextField()
    deadline = models.DateField()
    completed = models.BooleanField(default=False)
