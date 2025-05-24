from datetime import datetime, time
from typing import Optional
from django.utils import timezone
from teenApp.entities.task import Task
from teenApp.entities.task import TimeWindowRule


class TimeWindowUtils:
    """
    Static utilities to resolve and evaluate TimeWindowRules.
    """

    @staticmethod
    def resolve_rule(
        *,
        task: Optional[Task],
        window_type: str,
        when: Optional[datetime] = None,
    ) -> Optional[TimeWindowRule]:
        """
        Returns the most specific rule for a given task and time.
        Priority:
            1. task + specific_date
            2. task + weekday
            3. task (all days)
            4. global + specific_date
            5. global + weekday
            6. global (all days)
        """
        when = when or timezone.localtime()
        today = when.date()
        weekday = when.weekday()

        qs = TimeWindowRule.objects.filter(window_type=window_type)

        # Task + specific_date
        if task:
            rule = qs.filter(task=task, specific_date=today).first()
            if rule:
                return rule

            rule = qs.filter(task=task, weekday=weekday).first()
            if rule:
                return rule

            rule = qs.filter(task=task, specific_date__isnull=True, weekday__isnull=True).first()
            if rule:
                return rule

        # Global (no task)
        rule = qs.filter(task__isnull=True, specific_date=today).first()
        if rule:
            return rule

        rule = qs.filter(task__isnull=True, weekday=weekday).first()
        if rule:
            return rule

        return qs.filter(task__isnull=True, specific_date__isnull=True, weekday__isnull=True).first()

    @staticmethod
    def is_late(moment: datetime, rule: Optional[TimeWindowRule]) -> bool:
        """
        Returns True if the moment is outside the rule window.
        Handles scope enforcement:
            - rule applies ONLY if today matches rule's specific_date or weekday (if set).
        """
        if rule is None:
            return False

        today = moment.date()
        weekday = moment.weekday()

        # Rule is scoped to a specific date
        if rule.specific_date and rule.specific_date != today:
            return False

        # Rule is scoped to a weekday
        if rule.weekday is not None and rule.weekday != weekday:
            return False

        # Otherwise, compare time window
        t = moment.time()
        return not (rule.start_time <= t <= rule.end_time)

    @staticmethod
    def status_label(moment: datetime, rule: Optional[TimeWindowRule]) -> str:
        """
        Returns "late" or "on_time".
        """
        return "late" if TimeWindowUtils.is_late(moment, rule) else "on_time"
