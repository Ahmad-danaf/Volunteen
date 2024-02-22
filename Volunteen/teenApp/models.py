from django.db import models

# Create your models here.
class Task(models.Model):
 description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
 deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task',db_index=True)
 completed = models.BooleanField(default=False, verbose_name='Completed',help_text='Mark as completed')


