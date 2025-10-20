
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from childApp.models import Child
from teenApp.entities.task import Task, TaskProofRequirement
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import TimeWindowRule
from teenApp.utils.TimeWindowUtils import TimeWindowUtils
from django.utils import timezone

def process_check_in(task_completion_id):
    """
    Background post-processing for check-in.
    - Handles auto-approval logic.
    - Adds points if applicable.
    """
    tc = get_object_or_404(TaskCompletion, id=task_completion_id)
    task, child = tc.task, tc.child
    if task.proof_requirement == TaskProofRequirement.AUTO_ACCEPT_CHECKIN:
        tc.status = 'approved'
        total = (task.points or 0) + (tc.bonus_points or 0)
        tc.awarded_coins = total
        tc.remaining_coins = total
        child.add_points(total)
        tc.save()

    return f"Check-in processed for {child.user.username} ({tc.status})"

def process_check_out(task_completion_id):
    """
    Background post-processing for check-out.
    - Handles auto-approval logic.
    """
    tc = get_object_or_404(TaskCompletion, id=task_completion_id)
    task, child = tc.task, tc.child
    if task.proof_requirement == TaskProofRequirement.AUTO_ACCEPT_CHECKOUT:
        tc.status = 'approved'
        total = (task.points or 0) + (tc.bonus_points or 0)
        tc.awarded_coins = total
        tc.remaining_coins = total
        child.add_points(total)
        tc.save()

    return f"Check-out processed for {child.user.username} ({tc.status})"
