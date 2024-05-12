from django.db import models
from django.contrib.auth.models import User, Group
# Removed unnecessary import of `gettext_lazy` as it's not used

class Reward(models.Model):
    # Model representing a reward
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField("Image", upload_to='media/images/', null=True, blank=True)

    def __str__(self):
        return self.title

class Task(models.Model):
    description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
    deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task', db_index=True)
    completed = models.BooleanField(default=False, verbose_name='Completed', help_text='Mark as completed')
    title = models.CharField(max_length=200, verbose_name='Title')
    img = models.ImageField(verbose_name="Image", upload_to='media/images/', null=True, blank=True)
    points = models.IntegerField(verbose_name='Points', help_text='Enter the points for the task')
    duration = models.TextField(verbose_name='Duration', help_text='Enter the duration of the task')
    additional_details = models.TextField(verbose_name='Additional Details', help_text='Enter any additional details about the task', blank=True, null=True)
    task_id = models.IntegerField(unique=True, default=0, verbose_name='Task ID', help_text='Unique Task ID')
    completed_by = models.ManyToManyField('Child', related_name='tasks_completed', blank=True, verbose_name='Completed By')

    def __str__(self):
        return self.title

class Child(models.Model):
    # Model representing a child
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=0, verbose_name='Points')
    completed_tasks = models.ManyToManyField('Task', related_name='completed_by', blank=True, verbose_name='Completed Tasks')
    identifier = models.CharField(max_length=5, unique=True, verbose_name='Identifier')
    secret_code = models.CharField(max_length=3, verbose_name='Secret Code')

    def add_points(self, points):
        # Adds points to the child's total
        self.points += points
        self.save()

    def subtract_points(self, points):
        # Subtracts points from the child's total
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Add user to "Children" group
        children_group, created = Group.objects.get_or_create(name='Children')
        self.user.groups.add(children_group)

class Mentor(models.Model):
    # Model representing a mentor
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def assign_points_to_children(self, identifiers, task):
        # Assigns points to children based on task
        for identifier in identifiers:
            try:
                child = Child.objects.get(identifier=identifier)
                child.add_points(task.points)
                child.completed_tasks.add(task)
            except Child.DoesNotExist:
                print(f"Child with identifier {identifier} does not exist.")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Add user to "Mentor" group
        mentors_group, created = Group.objects.get_or_create(name='Mentors')
        self.user.groups.add(mentors_group)

class Shop(models.Model):
    # Model representing a shop
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
    # Model representing a redemption
    child = models.ForeignKey('Child', on_delete=models.CASCADE, verbose_name='Child')
    points_used = models.IntegerField(verbose_name='Points Used')
    date_redeemed = models.DateTimeField(auto_now_add=True, verbose_name='Date Redeemed')
    shop = models.ForeignKey('Shop', on_delete=models.CASCADE, verbose_name='Shop')  # Add the shop reference

    def __str__(self):
        return f'{self.child} redeemed {self.points_used} points at {self.shop} on {self.date_redeemed}'
