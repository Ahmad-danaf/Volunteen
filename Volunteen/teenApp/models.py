from django.db import models
from django.utils.translation import gettext_lazy as _

class Reward(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField(_("Image"), upload_to='media/images/', null=True, blank=True)


    def __str__(self):
        return self.title


class Task(models.Model):
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, verbose_name='Reward', help_text='Select reward for this task', blank=True, null=True)
    description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
    deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task', db_index=True)
    completed = models.BooleanField(default=False, verbose_name='Completed', help_text='Mark as completed')
    title = models.CharField(max_length=200)
    img = models.ImageField(_("Image"), upload_to='media/images/', null=True, blank=True)
    points = models.IntegerField(verbose_name='Points', help_text='Enter the points for the task')

    def __str__(self):
        return self.title


