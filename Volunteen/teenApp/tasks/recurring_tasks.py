from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django_q.tasks import async_task

from teenApp.entities import TimeWindowRule,TaskRecurrence, RecurringRun, Frequency
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils


class RecurringTaskUtils:
    """Handles auto-creation of recurring task instances."""

    @staticmethod
    def _log_run(task_template, period_start, status, reason=""):
        RecurringRun.objects.create(
            task_template=task_template,
            period_start=period_start,
            status=status,
            reason=reason[:500],
        )

    @staticmethod
    def _get_new_deadline(recurrence: TaskRecurrence) -> timezone.datetime.date:
        """
        Compute a new deadline date based on recurrence frequency.
        - DAILY → today
        - EVERY_X_DAYS → today + (interval_days - 1)
        - WEEKLY → today + 7
        - MONTHLY → today + 30 (approximation)
        """
        today = timezone.localdate()
        if recurrence.frequency == Frequency.DAILY:
            return today
        elif recurrence.frequency == Frequency.EVERY_X_DAYS:
            interval = recurrence.interval_days or 1
            return today + timedelta(days=interval - 1)
        elif recurrence.frequency == Frequency.WEEKLY:
            return today + timedelta(days=7)
        elif recurrence.frequency == Frequency.MONTHLY:
            return today + timedelta(days=30)
        return today + timedelta(days=1)

    @staticmethod
    def _clone_task_data(template_task, recurrence: TaskRecurrence):
        """
        Prepare a dict to re-create a task instance from a template.
        Dynamically adjusts the deadline based on recurrence frequency.
        """
        new_deadline = RecurringTaskUtils._get_new_deadline(recurrence)
        return {
            "title": template_task.title,
            "description": template_task.description,
            "additional_details": template_task.additional_details or "",
            "points": template_task.points,
            "deadline": new_deadline,
            "proof_requirement": template_task.proof_requirement,
            "proof_required": template_task.proof_required,
            "send_whatsapp_on_assign": template_task.send_whatsapp_on_assign,
            "is_pinned": template_task.is_pinned,
            "campaign": template_task.campaign,
            "img": template_task.img.name if template_task.img else 'defaults/no-image.png',
            "source_template": template_task,
            "_deduct_coins": recurrence.deduct_coins_on_create,
        }

    @staticmethod
    def recreate_due_tasks():
        now = timezone.now()
        due_recurrences = (
            TaskRecurrence.objects
            .select_related("task")
            .filter(is_active=True, next_run_at__lte=now)
        )

        for rec in due_recurrences:
            template = rec.task
            mentor = template.assigned_mentors.first()
            if not mentor:
                RecurringTaskUtils._log_run(template, now.date(), RecurringRun.Status.SKIPPED,
                                            "Template has no mentor assigned.")
                continue

            
            if rec.max_instances_per_period:
                count_today = RecurringRun.objects.filter(
                    task_template=template,
                    period_start=now.date(),
                ).count()
                if count_today >= rec.max_instances_per_period:
                    RecurringTaskUtils._log_run(template, now.date(), RecurringRun.Status.SKIPPED,
                                                "max_instances_per_period reached.")
                    rec.last_run_at = now
                    rec.next_run_at = rec.compute_next_run_at(from_dt_local=timezone.localtime(now))
                    rec.save(update_fields=["last_run_at", "next_run_at"])
                    continue

            children_ids = list(template.assigned_children.values_list("id", flat=True))
            timewindows = list(
                TimeWindowRule.objects.filter(task=template).values(
                    "start_time",
                    "end_time",
                    "weekday",
                    "specific_date",
                    "window_type",
                )
            )
            try:
                async_task(
                    MentorTaskUtils.create_task_with_assignments_async,
                    mentor.id,
                    children_ids,
                    RecurringTaskUtils._clone_task_data(template, rec),
                    timewindows,
                )
                RecurringTaskUtils._log_run(template, now.date(), RecurringRun.Status.CREATED)
                with transaction.atomic():
                    rec.last_run_at = now
                    rec.next_run_at = rec.compute_next_run_at(from_dt_local=timezone.localtime(now))
                    rec.save(update_fields=["last_run_at", "next_run_at"])

            except Exception as e:
                RecurringTaskUtils._log_run(template, now.date(), RecurringRun.Status.ERROR, str(e))
                print(f"[RecurringTaskUtils] ERROR creating from {template.id}: {e}")


    @staticmethod
    def recreate_due_tasks_longrun():
        """
        Wrapper that calls the recurring-task engine with an extended timeout.
        """
        async_task(
            RecurringTaskUtils.recreate_due_tasks,
            q_options={"timeout": 300},  # 5 minutes timeout
        )