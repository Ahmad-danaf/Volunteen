from django.db import models
from django.contrib.auth.models import User, Group
from Volunteen.constants import AVAILABLE_CITIES
from childApp.utilities.child_level_management import calculate_total_points

class Medal(models.Model):
    name = models.CharField(max_length=255, verbose_name='Medal Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    points_reward = models.IntegerField(default=0, verbose_name='Points Reward')
    criterion = models.CharField(max_length=255, verbose_name='Criterion Function')  # קריטריון לזכייה במדליה

    def __str__(self):
        return self.name


class Child(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    mentors = models.ManyToManyField("mentorApp.Mentor", related_name='children', blank=True, verbose_name='Mentors')
    points = models.IntegerField(default=0, verbose_name='Points')
    completed_tasks = models.ManyToManyField('teenApp.Task', related_name='completed_by_children', blank=True, verbose_name='Completed Tasks')
    identifier = models.CharField(max_length=5, unique=True, verbose_name='Identifier')
    secret_code = models.CharField(max_length=3, verbose_name='Secret Code')
    institution = models.ForeignKey("institutionApp.Institution", on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='Institution')
    parent = models.ForeignKey('parentApp.Parent', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='Parent')
    medals = models.ManyToManyField(Medal, blank=True, verbose_name='Medals')
    streak_count = models.IntegerField(default=0, verbose_name="Streak Count")
    last_streak_date = models.DateField(null=True, blank=True, verbose_name="Last Streak Date")
    city = models.CharField(
        max_length=3,
        choices=AVAILABLE_CITIES,
        verbose_name="City",
        blank=True,
        null=True,
    )
    @property
    def level(self):
        return (calculate_total_points(self) // 100) + 1
    def add_points(self, points):
        """
        Add points to the child and save changes.
        """
        self.points += points
        self.save()

    
    def subtract_points(self, points):
        """
        Subtract points from the child if there are enough points.
        """
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """
        Automatically add the child to the 'Children' group if not already added.
        """
        super().save(*args, **kwargs)
        children_group, created = Group.objects.get_or_create(name='Children')
        self.user.groups.add(children_group)
