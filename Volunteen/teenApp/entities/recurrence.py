from datetime import datetime, timedelta, time as dtime
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.utils import timezone

class Frequency(models.TextChoices):
        DAILY = "daily", "Daily" # every day
        EVERY_X_DAYS = "every_x_days", "Every X Days" # every N days
        WEEKLY = "weekly", "Weekly" # on selected weekdays
        MONTHLY = "monthly", "Monthly" # calendar day-of-month

class TaskRecurrence(models.Model):
    """Defines a recurrence pattern for a Task template, and tracks scheduling state."""
    
    task = models.OneToOneField(
        "teenApp.Task",
        on_delete=models.CASCADE,
        related_name="recurrence",
        help_text="Attach to a Task used as a template to clone from.",
    )

    # ---- Schedule definition ----
    frequency     = models.CharField(max_length=16, choices=Frequency.choices)
    interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Used only when frequency=every_x_days (>=1).",
    )
    by_weekday = models.JSONField(
        default=list, blank=True,
        help_text="Used only when frequency=weekly. Integers 0=Mon .. 6=Sun.",
    )
    day_of_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Used only when frequency=monthly. 1..28 recommended.",
    )

    run_time_local = models.TimeField(
        default=dtime(8, 0),
        help_text="Time of day to run (Israel local time). Default 08:00.",
    )
    start_date = models.DateField()
    end_date   = models.DateField(null=True, blank=True)

    # ---- Control ----
    is_active   = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(db_index=True, null=True, blank=True)

    # ---Behavior---
    deduct_coins_on_create = models.BooleanField(
        default=True, help_text="Charge mentor when an instance is created."
    )
    require_sufficient_balance = models.BooleanField(
        default=True, help_text="Skip creation if not enough TeenCoins."
    )
    max_instances_per_period = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Safety valve; typically leave empty."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_active", "next_run_at"]),
        ]
        constraints = [
                CheckConstraint(
                    name="rec_every_x_requires_interval",
                    check=Q(frequency=Frequency.EVERY_X_DAYS, interval_days__gte=1)
                        | ~Q(frequency=Frequency.EVERY_X_DAYS),
                ),
                CheckConstraint(
                    name="rec_monthly_dom_range",
                    check=Q(frequency=Frequency.MONTHLY, day_of_month__gte=1, day_of_month__lte=28)
                        | ~Q(frequency=Frequency.MONTHLY),
                ),
            ]
        verbose_name = "Task Recurrence"
        verbose_name_plural = "Task Recurrences"

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("end_date must be on/after start_date.")

        if self.frequency == Frequency.WEEKLY:
            if not isinstance(self.by_weekday, list) or not self.by_weekday:
                raise ValidationError("by_weekday must be a non-empty list for weekly.")
            if any((not isinstance(d, int) or d < 0 or d > 6) for d in self.by_weekday):
                raise ValidationError("by_weekday items must be integers 0..6.")

        if self.frequency == Frequency.EVERY_X_DAYS:
            if not self.interval_days or self.interval_days < 1:
                raise ValidationError("interval_days must be >= 1 for every_x_days.")

        if self.frequency == Frequency.MONTHLY:
            if not self.day_of_month:
                raise ValidationError("day_of_month is required for monthly.")
            if self.day_of_month < 1 or self.day_of_month > 28:
                raise ValidationError("day_of_month must be between 1 and 28.")

    def __str__(self):
        return f"Recurrence(task={self.task_id}, freq={self.frequency})"

    # ---- Scheduling helpers ----
    @staticmethod
    def _local_now():
        """Aware 'now' in the project's local timezone"""
        return timezone.localtime(timezone.now())

    def _combine_local(self, date_):
        """Return aware datetime in local tz for given date + run_time_local."""
        dt = datetime.combine(date_, self.run_time_local)
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def compute_next_run_at(self, from_dt_local: Optional[datetime] = None) -> Optional[datetime]:
        """
        Compute the next run datetime (aware) in local timezone.
        Caller can pass from_dt_local (aware, local tz) to base the computation from a point in time.
        """
        if not self.is_active:
            return None

        now_local = from_dt_local or self._local_now()
        cursor = max(now_local.date(), self.start_date)
        if self.end_date and cursor > self.end_date:
            return None

        def ok(dt_local):
            return dt_local > now_local and (not self.end_date or dt_local.date() <= self.end_date)

        # DAILY
        if self.frequency == Frequency.DAILY:
            candidate = self._combine_local(cursor)
            if ok(candidate):
                return candidate
            return self._combine_local(cursor + timedelta(days=1))

        # EVERY_X_DAYS
        if self.frequency == Frequency.EVERY_X_DAYS:
            k = 0
            # Find smallest k where start_date + k*interval is valid and in the future
            if self.interval_days:
                delta = (cursor - self.start_date).days
                k = max(0, (delta + self.interval_days - 1) // self.interval_days)
            while True:
                date_ = self.start_date + timedelta(days=k * (self.interval_days or 1))
                cand = self._combine_local(date_)
                if ok(cand):
                    return cand
                k += 1
                if self.end_date and date_ > self.end_date:
                    return None

        # WEEKLY
        if self.frequency == Frequency.WEEKLY:
            for add in range(0, 14):
                cand_date = cursor + timedelta(days=add)
                if cand_date.weekday() in (self.by_weekday or []):
                    cand = self._combine_local(cand_date)
                    if ok(cand):
                        return cand
            return None

        # MONTHLY
        if self.frequency == Frequency.MONTHLY:
            if not self.day_of_month:
                return None
            y, m = cursor.year, cursor.month
            for _ in range(0, 24):
                try:
                    date_ = datetime(y, m, self.day_of_month).date()
                except ValueError:
                    # (we already constrain to 1..28, so this should not trigger)
                    pass
                else:
                    cand = self._combine_local(date_)
                    if ok(cand):
                        return cand
                # move to next month
                m = 1 if m == 12 else m + 1
                y = y + 1 if m == 1 else y
            return None

        return None

    def save(self, *args, **kwargs):
        """
        Keep next_run_at fresh when active.
        We compute in local time; Django will store aware datetimes (UTC under the hood with USE_TZ=True).
        """
        if self.is_active:
            local_now = self._local_now()
            if not self.next_run_at or timezone.localtime(self.next_run_at) <= local_now:
                self.next_run_at = self.compute_next_run_at(from_dt_local=local_now)
        super().save(*args, **kwargs)


class RecurringRun(models.Model):
    """Audit log for each logical recurrence attempt/period of a template task."""

    class Status(models.TextChoices):
        CREATED = "created", "created"
        SKIPPED = "skipped", "skipped"
        ERROR   = "error",   "error"

    task_template = models.ForeignKey(
        "teenApp.Task",
        on_delete=models.CASCADE,
        related_name="recurring_runs",
        db_index=True,
        help_text="Template task that produced (or attempted to produce) an instance.",
    )
    period_start = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["task_template", "period_start"],
                name="uq_recurring_run_template_period",
            ),
        ]
        indexes = [
            models.Index(fields=["task_template", "-created_at"]),
        ]

    def __str__(self):
        return f"RecurringRun(template={self.task_template_id}, period={self.period_start}, status={self.status})"
