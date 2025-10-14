from datetime import datetime, time as dtime

from django.http import Http404

from teenApp.entities import TaskRecurrence, RecurringRun

class MentorTaskRecurrenceUtils:
    
    @staticmethod
    def _mentor_guard_qs(mentor):
        """
        Mentor-scoped queryset: only recurrences where the mentor is assigned to the template task.
        """
        return TaskRecurrence.objects.filter(task__assigned_mentors=mentor).select_related("task")

    @staticmethod
    def _parse_time_hhmm(value, default="08:00"):
        """
        Parse 'HH:MM' into datetime.time. Fallback to default if invalid.
        """
        s = str(value or default)
        try:
            h, m = map(int, s.split(":"))
            return dtime(h, m)
        except Exception:
            h, m = map(int, str(default).split(":"))
            return dtime(h, m)

    @staticmethod
    def _parse_date_yyyy_mm_dd(value):
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _int_or_none(v):
        try:
            return int(v) if v not in (None, "",) else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _int_list(values):
        if not isinstance(values, list):
            return []
        out = []
        for x in values:
            try:
                out.append(int(x))
            except (ValueError, TypeError):
                continue
        return out

    @staticmethod
    def _serialize_recurrence(rec: TaskRecurrence):
        """
        JSON-friendly shape the front-end needs for the dashboard cards.
        """
        task = rec.task
        return {
            "id": rec.id,
            "task_id": task.id,
            "task_title": task.title,
            "task_img": (getattr(task.img, "url", None) or ""),
            "frequency": rec.frequency,
            "frequency_display": rec.get_frequency_display(),
            "interval_days": rec.interval_days,
            "by_weekday": rec.by_weekday,
            "day_of_month": rec.day_of_month,
            "run_time_local": rec.run_time_local.strftime("%H:%M") if rec.run_time_local else None,
            "start_date": rec.start_date.isoformat() if rec.start_date else None,
            "end_date": rec.end_date.isoformat() if rec.end_date else None,
            "is_active": rec.is_active,
            "last_run_at": rec.last_run_at.isoformat() if rec.last_run_at else None,
            "next_run_at": rec.next_run_at.isoformat() if rec.next_run_at else None,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        }

    @staticmethod
    def _serialize_run(run: RecurringRun):
        return {
            "id": run.id,
            "task_template_id": run.task_template_id,
            "period_start": run.period_start.isoformat(),
            "status": run.status,
            "reason": run.reason,
            "created_at": run.created_at.isoformat(),
        }

    @staticmethod
    def _mentor_get_recurrence_or_404(mentor, rec_id: int) -> TaskRecurrence:
        try:
            return MentorTaskRecurrenceUtils._mentor_guard_qs(mentor).get(id=rec_id)
        except TaskRecurrence.DoesNotExist:
            raise Http404("Recurrence not found for this mentor")