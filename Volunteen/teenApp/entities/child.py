from django.db import models
from django.contrib.auth.models import User, Group


class Child(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mentors = models.ManyToManyField('Mentor', related_name='children', blank=True, verbose_name='Mentors')
    points = models.IntegerField(default=0, verbose_name='Points')
    completed_tasks = models.ManyToManyField('Task', related_name='completed_by_children', blank=True, verbose_name='Completed Tasks')
    identifier = models.CharField(max_length=5, unique=True, verbose_name='Identifier')
    secret_code = models.CharField(max_length=3, verbose_name='Secret Code')

    def add_points(self, points):
        self.points += points
        self.save()

    def subtract_points(self, points):
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        children_group, created = Group.objects.get_or_create(name='Children')
        self.user.groups.add(children_group)
