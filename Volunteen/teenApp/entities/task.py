from django.db import models
from django.utils import timezone

class Task(models.Model):
    description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
    deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task', db_index=True)
    completed = models.BooleanField(default=False, verbose_name='Completed', help_text='Mark as completed')
    title = models.CharField(max_length=200, verbose_name='Title')
    img = models.ImageField(verbose_name="Image", upload_to='media/images/', null=True, blank=True, default='defaults/no-image.png')
    points = models.IntegerField(verbose_name='Points', help_text='Enter the points for the task')
    duration = models.TextField(verbose_name='Duration', help_text='Enter the duration of the task')
    additional_details = models.TextField(verbose_name='Additional Details', help_text='Enter any additional details about the task', blank=True, null=True)
    completed_by = models.ManyToManyField('Child', related_name='tasks_completed', blank=True, verbose_name='Completed By')
    assigned_children = models.ManyToManyField('Child', related_name='assigned_tasks', blank=True, verbose_name='Assigned Children')
    assigned_mentors = models.ManyToManyField('Mentor', related_name='assigned_tasks', blank=True, verbose_name='Assigned Mentors')
    new_task = models.BooleanField(default=True, verbose_name='New Task', help_text='Indicates if the task is new for the child')
    viewed = models.BooleanField(default=False, verbose_name='Viewed', help_text='Indicates if the child has viewed the task')
    total_bonus_points = models.IntegerField(default=0, verbose_name='Total Bonus Points', help_text='Total bonus points assigned to this task')
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name='Completed Date', help_text='The date when the task was completed')
    admin_max_points= models.IntegerField(default=0, verbose_name='Max Bonus Points', help_text='Max bonus points assigned to this task')
    def __str__(self):
        return self.title

    def is_overdue(self):
        return timezone.now().date() > self.deadline
