from django.db import models
from django.utils import timezone
from teenApp.entities.TaskCompletion import TaskCompletion


class TaskProofRequirement(models.TextChoices):
    CAMERA_ONLY = "camera", "העלאת תמונה מהמצלמה בלבד"
    CAMERA_OR_GALLERY = "gallery", "תמונה מהמצלמה או הגלריה"
    AUTO_ACCEPT_CHECKIN = "auto_checkin", "מאושר אוטומטית אחרי Check-in"
    AUTO_ACCEPT_CHECKOUT = "auto_checkout", "מאושר אוטומטית אחרי Check-out"
    NO_PROOF_REQUIRED = "none", "ללא צורך בהעלאת תמונה  "


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
    completed_date = models.DateTimeField(null=True, blank=True, verbose_name='Completed Date', help_text='The date when the task was completed')
    is_template=models.BooleanField(default=False, verbose_name='Template', help_text='Mark as a template for future duplication')
    is_pinned = models.BooleanField(default=False, verbose_name='Pinned', help_text='Pin this task to highlight it for mentors and children')
    campaign = models.ForeignKey(
        "shopApp.Campaign", null=True, blank=True,
        on_delete=models.CASCADE, related_name="tasks"
    )
    proof_required  = models.BooleanField(default=True)
    send_whatsapp_on_assign = models.BooleanField(
        default=True,
        verbose_name="Send WhatsApp notification when task is assigned",
        help_text="If checked, an automatic WhatsApp message will be sent to the user when a task is assigned to them"
    )
    proof_requirement = models.CharField(
        max_length=20,
        choices=TaskProofRequirement.choices,
        default=TaskProofRequirement.CAMERA_ONLY,
        verbose_name="דרישת הוכחה",
        help_text="בחר את סוג ההוכחה הנדרשת מהחניך",
    )
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
        

# • If specific_date is set → rule applies only that calendar day.
# • Else, if weekday is set → rule recurs every week on that weekday.
# • Else → rule applies every day.
class TimeWindowRule(models.Model):
    class WindowType(models.TextChoices):
        CHECK_IN  = "check_in",  "Check-in"
        CHECK_OUT = "check_out", "Check-out"

    task = models.ForeignKey(
        "teenApp.Task",
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="time_window_rules"
    )

    specific_date = models.DateField(null=True, blank=True)
    weekday = models.PositiveSmallIntegerField(null=True, blank=True)

    window_type = models.CharField(max_length=10, choices=WindowType.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "window_type"],
                name="unique_timewindow_per_type_per_task"
            )
        ]
        unique_together = ("task", "specific_date", "weekday", "window_type")

    def __str__(self):
        scope = (
            f"date {self.specific_date}"
            if self.specific_date
            else f"weekday {self.weekday}"
            if self.weekday is not None
            else "all days"
        )
        task_part = f"{self.task.title}" if self.task else ""
        return f"{task_part} • {scope} • {self.get_window_type_display()}"