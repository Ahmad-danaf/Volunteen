from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from mentorApp.models import Mentor
from parentApp.models import Parent
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion


class Command(BaseCommand):
    help = "Refund teencoins for overdue tasks not completed after 4 days and reject unapproved TaskCompletions"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        assignments = TaskAssignment.objects.filter(
            task__deadline__lt=today - timedelta(days=4)
        )
        self.stdout.write("############# refund overdue tasks ##############")
        self.stdout.write(f"Found {assignments.count()} overdue tasks.")
        for assignment in assignments:
            # Skip if task has already been approved
            if TaskCompletion.objects.filter(
                child=assignment.child,
                task=assignment.task,
                status='approved'
            ).exists():
                continue

            # Reject unapproved TaskCompletions
            completions_to_reject = TaskCompletion.objects.filter(
                child=assignment.child,
                task=assignment.task
            ).exclude(status='approved')

            for completion in completions_to_reject:
                previous_status = completion.status
                completion.status = 'rejected'
                completion.save()
                self.stdout.write(
                    f"[REJECTED] TaskCompletion for '{assignment.task.title}' by '{assignment.child.user.username}' changed from '{previous_status}' to 'rejected'."
                )

            refund_entities = []
            if assignment.assigned_by:
                try:
                    mentor = Mentor.objects.get(user=assignment.assigned_by)
                    refund_entities.append(mentor)
                except Mentor.DoesNotExist:
                    try:
                        parent = Parent.objects.get(user=assignment.assigned_by)
                        refund_entities.append(parent)
                    except Parent.DoesNotExist:
                        self.stdout.write(f"[SKIP] User {assignment.assigned_by} is neither Mentor nor Parent.")
                        continue
            else:
                refund_entities.extend(assignment.task.assigned_mentors.all())

            for entity in refund_entities:
                try:
                    entity.available_teencoins += assignment.task.points
                    entity.save()
                    self.stdout.write(
                        f"[OK] Refunded {assignment.task.points} teencoins to {entity.user.username} "
                        f"for task '{assignment.task.title}' assigned to child '{assignment.child.user.username}'."
                    )
                except Exception as e:
                    self.stderr.write(
                        f"[ERROR] Failed to refund {assignment.task.points} teencoins to {entity.user.username if hasattr(entity, 'user') else 'Unknown'} "
                        f"for task '{assignment.task.title}': {str(e)}"
                    )
        self.stdout.write("############# end refund overdue tasks ##############")
