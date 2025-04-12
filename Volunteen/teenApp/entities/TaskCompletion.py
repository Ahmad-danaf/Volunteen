from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
import os

class TaskCompletion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
    ]

    child = models.ForeignKey('childApp.Child', on_delete=models.CASCADE)
    task = models.ForeignKey('teenApp.Task', on_delete=models.CASCADE)
    completion_date = models.DateTimeField(default=timezone.now)
    bonus_points = models.IntegerField(default=0)
    remaining_coins = models.IntegerField(default=0, help_text="Unredeemed TeenCoins from this task.")
    checkin_img = models.ImageField(upload_to='checkin_images/', null=True, blank=True, verbose_name='Check-In Image')
    checkout_img = models.ImageField(upload_to='checkout_images/', null=True, blank=True, verbose_name='Check-Out Image')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    mentor_feedback = models.TextField(null=True, blank=True, verbose_name='Mentor Feedback')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='approved_tasks', null=True, blank=True)


    class Meta:
        unique_together = ('child', 'task')  # Ensure that each child can only complete a task once

    def __str__(self):
        return f"{self.child.user.username} - {self.task.title} ({self.status})"

        
    def init_remaining_coins(self):
        """ Initialize remaining_coins to the sum of points and bonus points. """
        self.remaining_coins = self.bonus_points + self.task.points
        self.save()

    def is_expired(self):
        """ Check if the TeenCoins from this task have expired (3 months limit). """
        return self.completion_date + relativedelta(months=3) < timezone.now()


    def delete(self, *args, **kwargs):
        if self.checkin_img and os.path.exists(self.checkin_img.path):
            os.remove(self.checkin_img.path)
        if self.checkout_img and os.path.exists(self.checkout_img.path):
            os.remove(self.checkout_img.path)
        super().delete(*args, **kwargs)
