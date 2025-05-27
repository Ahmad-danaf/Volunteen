from datetime import datetime, date
from typing import Optional
from django.utils import timezone
from teenApp.entities.task import Task, TimeWindowRule

class TimeWindowUtils:
    """
    Utilities for handling time window validation logic.
    """

    @staticmethod
    def get_rule(task: Task, window_type: str) -> Optional[TimeWindowRule]:
        """
        Returns the TimeWindowRule for the given task and type, if it exists.
        """
        return task.time_window_rules.filter(window_type=window_type).first()


    @staticmethod
    def is_late(task: Task, window_type: str, check_time: datetime) -> bool:
        """
        Determine if a given check_time (check-in or check-out) is late for the task.
        """
        rule = TimeWindowUtils.get_rule(task, window_type)

        if not rule:
            # No time window rule → allowed anytime until deadline
            return check_time.date() > task.deadline

        check_time = timezone.localtime(check_time)
        check_date = check_time.date()
        check_weekday = check_date.weekday()

        # Rule with specific date
        if rule.specific_date:
            if check_date != rule.specific_date:
                return True  # Wrong date
        # Rule with weekday
        elif rule.weekday is not None:
            if check_weekday != rule.weekday:
                return True  # Wrong weekday

        # Time range check
        start_dt = datetime.combine(check_date, rule.start_time, tzinfo=check_time.tzinfo)
        end_dt = datetime.combine(check_date, rule.end_time, tzinfo=check_time.tzinfo)

        return not (start_dt <= check_time <= end_dt)
