from datetime import time
from django.core.exceptions import ValidationError
from django.db import models

class TaskRecurrence(models.Model):
    # Frequencies we support
    FREQ_DAILY       = "daily"          # every day
    FREQ_EVERY_X     = "every_x_days"   # every N days
    FREQ_WEEKLY      = "weekly"         # on selected weekdays
    FREQ_MONTHLY     = "monthly"        # calendar day-of-month
    FREQ_CHOICES = [
        (FREQ_DAILY,   "daily"),
        (FREQ_EVERY_X, "every_x_days"),
        (FREQ_WEEKLY,  "weekly"),
        (FREQ_MONTHLY, "monthly"),
    ]

    task = models.OneToOneField(
        "teenApp.Task",
        on_delete=models.CASCADE,
        related_name="recurrence",
        help_text="Attach to a Task set as is_template=True",
    )

    # Schedule definition
    frequency = models.CharField(max_length=16, choices=FREQ_CHOICES)
    interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Used only when frequency=every_x_days (>=1)."
    )
    by_weekday = models.JSONField(
        default=list, blank=True,
        help_text="Used only when frequency=weekly. Integers 0=Mon .. 6=Sun."
    )
    day_of_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Used only when frequency=monthly. 1..28 recommended."
    )

    run_time_local = models.TimeField(default=time(8, 0), help_text="Local time (default 08:00).")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    # Control
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(db_index=True, null=True, blank=True)

    # Coins behavior
    deduct_coins_on_create = models.BooleanField(
        default=True,
        help_text="If true, charge parent/mentor when an instance is created."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "next_run_at"]),
        ]
        verbose_name = "Task Recurrence"
        verbose_name_plural = "Task Recurrences"

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("end_date must be on/after start_date.")

        if self.frequency == self.FREQ_EVERY_X:
            if not self.interval_days or self.interval_days < 1:
                raise ValidationError("interval_days must be >= 1 for every_x_days.")

        if self.frequency == self.FREQ_WEEKLY:
            if not isinstance(self.by_weekday, list) or not self.by_weekday:
                raise ValidationError("by_weekday must be a non-empty list for weekly.")
            if any((not isinstance(d, int) or d < 0 or d > 6) for d in self.by_weekday):
                raise ValidationError("by_weekday items must be integers 0..6.")

        if self.frequency == self.FREQ_MONTHLY:
            if not self.day_of_month:
                raise ValidationError("day_of_month is required for monthly.")
            if self.day_of_month < 1 or self.day_of_month > 28:
                raise ValidationError("day_of_month must be between 1 and 28.")

    def __str__(self):
        return f"Recurrence(task={self.task_id}, freq={self.frequency})"


class RecurringRun(models.Model):
    STATUS_CREATED = "created"
    STATUS_SKIPPED = "skipped"
    STATUS_ERROR   = "error"

    task_template = models.ForeignKey("teenApp.Task", on_delete=models.CASCADE, related_name="recurring_runs")
    period_start  = models.DateField()  
    status        = models.CharField(max_length=16, choices=[
        (STATUS_CREATED, "created"),
        (STATUS_SKIPPED, "skipped"),
        (STATUS_ERROR,   "error"),
    ])
    reason        = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("task_template", "period_start")
