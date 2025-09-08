from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

from teenApp.entities import TaskRecurrence, RecurringRun, Task
from teenApp.utils.TaskManagerUtils import TaskManagerUtils  
from mentorApp.utils import MentorTaskUtils
from parentApp.utils import ParentTaskUtils

class RecurringMaterializer:
    """
    Safely materializes due TaskRecurrence rows:
      - Row-level locking with skip_locked to avoid double work
      - Per (template, day) idempotency via RecurringRun unique_together
      - Owner routing: Mentor vs Parent
      - Advances next_run_at in local time (Asia/Jerusalem) -> stored as UTC
    """

    @classmethod
    def process_due(cls, batch_size: int = 100) -> None:
        now = timezone.now()
        # LOCK only the due subset; safe under multiple workers
        due_qs = (
            TaskRecurrence.objects
            .filter(is_active=True, next_run_at__isnull=False, next_run_at__lte=now)
            .select_for_update(skip_locked=True)       
            .select_related("task")
            .order_by("next_run_at")[:batch_size]
        )

        for rec in due_qs:
            try:
                cls._process_one(rec, now=now)
            except Exception:
                print(f"Error processing recurrence {rec.id}:")

    @classmethod
    @transaction.atomic
    def _process_one(cls, rec: TaskRecurrence, now=None) -> None:
        now = now or timezone.now()
        rec = (
            TaskRecurrence.objects
            .select_for_update(skip_locked=True)
            .select_related("task")
            .get(id=rec.id)
        )
        template: Task | None = rec.task
        assigned_children = list(template.assigned_children.all())
        # Hard safety checks
        if not template:
            cls._record_skip(rec, reason="Missing template task.")
            return
        if not template.is_template:
            cls._record_skip(rec, reason=f"Task {template.id} is not a template.")
            return
        if not rec.is_active:
            cls._record_skip(rec, reason="Recurrence inactive.")
            return
        if rec.end_date and rec.end_date < rec.start_date:
            cls._record_skip(rec, reason="Invalid date range (end_date < start_date).")
            return
        if rec.next_run_at is None or rec.next_run_at > now:
            cls._record_skip(rec, reason="Not due yet.")
            return
        if not assigned_children:
            cls._record_skip(rec, reason="Template has no assigned children.")
            rec.last_run_at = now
            rec.next_run_at = cls._compute_next_run_at(rec, from_dt=now)
            rec.save(update_fields=["last_run_at", "next_run_at"])
            run.status = RecurringRun.STATUS_SKIPPED
            run.reason = "No children assigned on template."
            run.save(update_fields=["status", "reason"])
            return

        # Idempotency barrier per (template, day)
        occ_date = timezone.localdate(rec.next_run_at)
        run, created = RecurringRun.objects.get_or_create(
            task_template=template,
            period_start=occ_date,
            defaults={"status": RecurringRun.STATUS_CREATED, "reason": ""},
        )
        if not created:
            # Already processed/attempted by another worker earlier—just advance schedule.
            rec.last_run_at = now
            rec.next_run_at = cls._compute_next_run_at(rec, from_dt=now)
            rec.save(update_fields=["last_run_at", "next_run_at"])
            return

        try:
            is_mentor_owned = TaskManagerUtils.is_task_assigned_to_any_mentor(template)
            scheduled_for = timezone.localdate(rec.next_run_at)
            assigned_mentors = list(template.assigned_mentors.all())

            extra_task_data = {
                "scheduled_for": scheduled_for,
                "source_template": template,
                "created_by": template.created_by,
                "created_by_recurrence": True, 
                "title": template.title,
            }
            timewindow_data = [
                {
                    "window_type":   r.window_type,                                  
                    "specific_date": r.specific_date, 
                    "weekday":       r.weekday,     
                    "start_time":    r.start_time,
                    "end_time":      r.end_time,
                }
                for r in template.time_window_rules.all()
            ]
            if is_mentor_owned:
                MentorTaskUtils.create_task_with_assignments(
                    template_task=template,
                    assigned_mentors=assigned_mentors,
                    assigned_children=assigned_children,
                    extra_task_data=extra_task_data,
                    recurrence_run=run,
                    deduct_coins=rec.deduct_coins_on_create,
                    timewindow_data=timewindow_data,
                )
            else:
                #TODO: handle case where no parent exists
                pass
        
            # Success -> advance schedule
            rec.last_run_at = now
            rec.next_run_at = cls._compute_next_run_at(rec, from_dt=now)
            rec.save(update_fields=["last_run_at", "next_run_at"])

            run.status = RecurringRun.STATUS_CREATED
            run.reason = ""
            run.save(update_fields=["status", "reason"])

        except Exception as e:
            run.status = RecurringRun.STATUS_ERROR
            run.reason = (str(e) or "Unknown error")[:500]
            run.save(update_fields=["status", "reason"])

            rec.next_run_at = cls._compute_next_run_at(rec, from_dt=now + timedelta(minutes=5))
            rec.save(update_fields=["next_run_at"])
            raise  

    @staticmethod
    def _record_skip(rec: TaskRecurrence, reason: str) -> None:
        # “skip” row for visibility; ties it to *today* so you can see why it didn’t run.
        try:
            RecurringRun.objects.get_or_create(
                task_template=rec.task,
                period_start=timezone.localdate(),
                defaults={"status": RecurringRun.STATUS_SKIPPED, "reason": reason[:500]},
            )
        except Exception:
            # don't let bookkeeping break the job
            pass



    @staticmethod
    def _compute_next_run_at(rec: TaskRecurrence, from_dt: datetime | None = None):
        """
        Compute the next occurrence (local schedule) and return UTC datetime.
        Looks forward up to ~400 days to be safe.
        """
        from_dt = from_dt or timezone.now()
        local_now = timezone.localtime(from_dt)
        start_date = max(rec.start_date, local_now.date())

        for offset in range(0, 400):
            candidate = start_date + timedelta(days=offset)
            if _is_due_on(rec, candidate):
                target_local = datetime.combine(candidate, rec.run_time_local)
                target_local = timezone.make_aware(target_local) 
                if target_local <= local_now:
                    continue
                return target_local
        return None


# #######helper functions#####################


def _is_due_on(rec: TaskRecurrence, date_):
    if rec.end_date and date_ > rec.end_date:
        return False
    if date_ < rec.start_date:
        return False

    f = rec.frequency
    if f == TaskRecurrence.FREQ_DAILY:
        return True
    if f == TaskRecurrence.FREQ_EVERY_X:
        if not rec.interval_days or rec.interval_days < 1:
            return False
        delta = (date_ - rec.start_date).days
        return delta >= 0 and (delta % rec.interval_days == 0)
    if f == TaskRecurrence.FREQ_WEEKLY:
        return date_.weekday() in (rec.by_weekday or [])
    if f == TaskRecurrence.FREQ_MONTHLY:
        return date_.day == rec.day_of_month
    return False
