from django.db import models
from django.utils import timezone
from teenApp.entities.TaskCompletion import TaskCompletion

class Task(models.Model):
    title = models.CharField(max_length=200, verbose_name='Title')
    deadline = models.DateField(verbose_name='Deadline', help_text='Specify the deadline for the task', db_index=True)
    completed = models.BooleanField(default=False, verbose_name='Completed', help_text='Mark as completed')
    description = models.TextField(verbose_name='Task Description', help_text='Enter the task details')
    additional_details = models.TextField(verbose_name='Additional Details', help_text='Enter any additional details about the task', blank=True, null=True)
    points = models.IntegerField(verbose_name='Points', help_text='Enter the points for the task')
    img = models.ImageField(verbose_name="Image", upload_to='media/images/', null=True, blank=True, default='defaults/no-image.png')
    assigned_children = models.ManyToManyField('childApp.Child', related_name='assigned_tasks', verbose_name='Assigned Children', blank=True)
    assigned_mentors = models.ManyToManyField('mentorApp.Mentor', related_name='assigned_tasks', blank=True, verbose_name='Assigned Mentors')
    total_bonus_points = models.IntegerField(default=0, verbose_name='Total Bonus Points', help_text='Total bonus points assigned to this task')
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name='Completed Date', help_text='The date when the task was completed')
    admin_max_points = models.IntegerField(default=0, verbose_name='Max Bonus Points', help_text='Max bonus points assigned to this task')

    def __str__(self):
        return self.title

    def is_overdue(self):
        return timezone.now().date() > self.deadline

    def mark_completed(self, child):
        """Mark the task as completed by a specific child."""
        task_completion, created = TaskCompletion.objects.get_or_create(task=self, child=child)

        if created:
            child.add_points(self.points)  # Add points to the child
            self.assigned_children.remove(child)  # Remove child from assigned children
            self.save()  # Save changes

    def approve_task(self, child):
        """Approve a task for a specific child."""
        task_completion = TaskCompletion.objects.filter(task=self, child=child).first()
        if task_completion and task_completion.status == 'pending':
            task_completion.status = 'approved'
            task_completion.save()
            child.add_points(self.points)

    def reject_task(self, child, feedback=None):
        """Reject a task for a specific child."""
        task_completion = TaskCompletion.objects.filter(task=self, child=child).first()
        if task_completion and task_completion.status == 'pending':
            task_completion.status = 'rejected'
            task_completion.mentor_feedback = feedback
            task_completion.save()
    def mark_as_new(self, child):
        """Mark the task as new for a specific child."""
        self.new_for_children.add(child)
        self.save()
            
    def mark_as_viewed(self, child):
        """Mark the task as viewed (not new) for a specific child."""
        self.new_for_children.remove(child)
        self.save()