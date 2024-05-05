from django.db import models
from django.contrib.auth.models import User, Group
from django.utils.translation import gettext_lazy as _

class Reward(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField(_("Image"), upload_to='media/images/', null=True, blank=True)
    def _str_(self):
        return self.title
class Task(models.Model):
    reward = models.ForeignKey('Reward', on_delete=models.CASCADE, verbose_name='Reward', help_text='Select reward for this task', blank=True, null=True)
    description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
    deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task', db_index=True)
    completed = models.BooleanField(default=False, verbose_name='Completed', help_text='Mark as completed')
    title = models.CharField(max_length=200, verbose_name='Title')
    img = models.ImageField(verbose_name="Image", upload_to='media/images/', null=True, blank=True)
    points = models.IntegerField(verbose_name='Points', help_text='Enter the points for the task')
    duration = models.TextField(verbose_name='Duration', help_text='Enter the duration of the task')
    additional_details = models.TextField(verbose_name='Additional Details', help_text='Enter any additional details about the task', blank=True, null=True)

    def _str_(self):
        return self.title
    
class Child(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0, verbose_name='Points')
    completed_tasks = models.ManyToManyField('Task', related_name='completed_by', blank=True, verbose_name='Completed Tasks')
    identifier = models.CharField(max_length=5, unique=True, verbose_name='Identifier', default='00000')
    secret_code = models.CharField(max_length=3, verbose_name='Secret Code', default='000')

    def add_points(self, points):
        
        self.points += points
        self.save()

    def subtract_points(self, points):
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract")

    def _str_(self):
        return self.user.username
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Add user to "Mentor" group
        children_group, created = Group.objects.get_or_create(name='Children')
        self.user.groups.add(children_group)


class Mentor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def assign_points_to_children(self, identifiers, task):
        for identifier in identifiers:
            try:
                child = Child.objects.get(identifier=identifier)
                child.add_points(task.points)
                child.completed_tasks.add(task)
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")

    def _str_(self):
        return self.user.username
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Add user to "Mentor" group
        mentors_group, created = Group.objects.get_or_create(name='Mentors')
        self.user.groups.add(mentors_group)
    
    
    
class Shop(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Add user to "Shops" group
        shops_group, created = Group.objects.get_or_create(name='Shops')
        self.user.groups.add(shops_group)
    
    
class Redemption(models.Model):
    child = models.ForeignKey('Child', on_delete=models.CASCADE, verbose_name='Child')
    points_used = models.IntegerField(verbose_name='Points Used')
    date_redeemed = models.DateTimeField(auto_now_add=True, verbose_name='Date Redeemed')
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, verbose_name='Shop')  # Add the shop reference

    def __str__(self):
        return f'{self.child} redeemed {self.reward} for {self.points_used} points at {self.shop} on {self.date_redeemed}'
