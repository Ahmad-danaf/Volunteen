from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class TaskCompletion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    child = models.ForeignKey('childApp.Child', on_delete=models.CASCADE)
    task = models.ForeignKey('teenApp.Task', on_delete=models.CASCADE)
    completion_date = models.DateTimeField(default=timezone.now)
    bonus_points = models.IntegerField(default=0)
    remaining_coins = models.IntegerField(default=0, help_text="Unredeemed TeenCoins from this task.")
    checkin_img = models.ImageField(upload_to='checkin_images/', null=True, blank=True, verbose_name='Check-In Image')
    checkout_img = models.ImageField(upload_to='checkout_images/', null=True, blank=True, verbose_name='Check-Out Image')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    mentor_feedback = models.TextField(null=True, blank=True, verbose_name='Mentor Feedback')

    class Meta:
        unique_together = ('child', 'task')  # Ensure that each child can only complete a task once

    def __str__(self):
        return f"{self.child.user.username} - {self.task.title} ({self.status})"

    def save(self, *args, **kwargs):
        """ Automatically initialize remaining_coins when a task is approved. """
        if self.status == "approved" and self.remaining_coins == 0 and not self.pk:
            self.remaining_coins = self.bonus_points + self.task.points
        elif self.status == "rejected":
            self.remaining_coins = 0  # Reset if rejected
        super().save(*args, **kwargs)

    def is_expired(self):
        """ Check if the TeenCoins from this task have expired (3 months limit). """
        return self.completion_date + relativedelta(months=3) < timezone.now()
