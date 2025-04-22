from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.db import models
from childApp.models import Child
from mentorApp.models import Mentor                     
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from shopApp.models import Campaign                    
from Volunteen.constants import CAMPAIGN_MENTOR_USERNAME, CAMPAIGN_TIME_LIMIT_MINUTES

class CampaignUtils:

    @staticmethod
    def get_campaign_mentor() -> Mentor:
        """
        Return (and lazily create, if missing) the virtual Mentor used to assign
        campaign tasks. Keeps real mentors’ stats clean.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user, _ = User.objects.get_or_create(username=CAMPAIGN_MENTOR_USERNAME,
                                            defaults={"email": "",
                                                    "is_active": False})
        mentor, _ = Mentor.objects.get_or_create(user=user)
        return mentor

    @staticmethod
    def current_approved_children_qs(campaign: Campaign):
        """
        Children who still hold a valid slot:
        - They have at least one TaskAssignment for this campaign
        AND it’s not expired by assigned_at
        - They have NO rejected TaskCompletion for this campaign
        Returns a .values('child').distinct() QuerySet, so you can call .count()
        """
        cutoff = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES)

        valid = TaskAssignment.objects.filter(
            task__campaign=campaign,
            assigned_at__gte=cutoff
        )

        rejected_children = TaskCompletion.objects.filter(
            task__campaign=campaign,
            status="rejected"
        ).values_list("child", flat=True).distinct()

        return (
            valid
            .exclude(child__in=rejected_children)
            .values("child")
            .distinct()
        )


    @staticmethod
    @transaction.atomic
    def join_campaign(child: Child, campaign: Campaign):
        """
        Reserve a slot and assign every task in the campaign to *child*.

        Raises:
            ValueError – if limit reached or child already holds an active slot.
        """
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)

        if CampaignUtils.current_approved_children_qs(campaign).filter(child=child.pk).exists():
            raise ValueError("Child already joined this campaign.")

        current_slots = CampaignUtils.current_approved_children_qs(campaign).count()
        if campaign.max_children and current_slots >= campaign.max_children:
            raise ValueError("Campaign is full.")

        mentor = CampaignUtils.get_campaign_mentor()
        assignments = [
            TaskAssignment(
                child=child,
                task=task,
                assigned_by=mentor.user,  
            )
            for task in campaign.tasks.all()
        ]
        TaskAssignment.objects.bulk_create(assignments, ignore_conflicts=True)

        return len(assignments) 


    @staticmethod
    def expire_campaign_reservations(minutes: int = CAMPAIGN_TIME_LIMIT_MINUTES) -> int:
        """
        Expire all campaign slots globally.

        A child loses their slot if:
        - Any of their campaign tasks was rejected
        - OR they exceeded the time limit and not all tasks are mentor-approved

        If expired, we also mark their TaskCompletions with a note.

        Returns: number of TaskAssignments deleted
        """
        cutoff = timezone.localtime(timezone.now()) - timedelta(minutes=minutes)

        expired_assignments = TaskAssignment.objects.none()

        for campaign in Campaign.objects.filter(is_active=True):
            campaign_tasks = campaign.tasks.all()
            total_tasks = campaign_tasks.count()
            if total_tasks == 0:
                continue

            child_assignments = (
                TaskAssignment.objects
                .filter(task__in=campaign_tasks)
                .values("child")
                .annotate(assignment_count=Count("id"))
            )

            for child_group in child_assignments:
                child_id = child_group["child"]

                assignments = TaskAssignment.objects.filter(
                    child_id=child_id, task__campaign=campaign
                )

                # Check if any task is rejected
                rejected_qs = TaskCompletion.objects.filter(
                    task__campaign=campaign,
                    child_id=child_id,
                    status="rejected"
                )
                if rejected_qs.exists():
                    expired_assignments |= assignments
                    continue

                # Check time expiration + not fully approved
                first_assignment = assignments.order_by("assigned_at").first()
                if not first_assignment:
                    continue

                if first_assignment.assigned_at < cutoff:
                    approved_task_ids = TaskCompletion.objects.filter(
                        child_id=child_id,
                        task__campaign=campaign,
                        status="approved"
                    ).values_list("task_id", flat=True).distinct()

                    if approved_task_ids.count() < total_tasks:
                        expired_assignments |= assignments

                        TaskCompletion.objects.filter(
                            child_id=child_id,
                            task__campaign=campaign
                        ).update(
                            status="rejected",
                            mentor_feedback=models.F("mentor_feedback") + "\n[נדחה אוטומטית על ידי המערכת עקב חוסר השלמה בזמן]"
                        )

        deleted_count = expired_assignments.count()
        expired_assignments.delete()
        return deleted_count

    
    @staticmethod
    def get_time_left(child: Child, campaign: Campaign) -> "timedelta | None":
        """
        How long until the child's reservation expires, or None if not joined.
        """
        assignment = (
            TaskAssignment.objects
            .filter(child=child, task__campaign=campaign)
            .order_by("assigned_at")
            .first()
        )
        if not assignment:
            return None
        deadline = assignment.assigned_at + timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES)
        return max(deadline - timezone.localtime(timezone.now()), timedelta(0))

    @staticmethod
    def child_has_finished(child: Child, campaign: Campaign) -> bool:
        """
        True if *every* campaign task for this child is mentor-approved.
        """
        total = campaign.tasks.count()
        approved_count = TaskCompletion.objects.filter(
            child=child,
            task__campaign=campaign,
            status="approved"
        ).values("task_id").distinct().count()

        return total > 0 and approved_count == total
    
    
    @staticmethod
    def child_has_joined(child: Child, campaign: Campaign) -> bool:
        """
        True if *any* campaign task for this child is mentor‑approved.
        """
        return TaskAssignment.objects.filter(
            child=child,
            task__campaign=campaign
        ).exists()


    @staticmethod
    @transaction.atomic
    def leave_campaign(child: Child, campaign: Campaign) -> int:
        """
        Fully removes a child from a campaign:
        - Deletes all TaskAssignments for this child in the campaign
        - Optionally marks TaskCompletions as rejected with feedback

        Returns: number of assignments deleted
        """
        assignments = TaskAssignment.objects.filter(
            child=child,
            task__campaign=campaign
        )
        
        completions = TaskCompletion.objects.filter(
            task__campaign=campaign,
            child=child
        )
        for c in completions:
            if c.status != "approved":
                c.status = "rejected"
                existing = c.mentor_feedback or ""
                suffix = "\n[נדחה אוטומטית על ידי המערכת עקב הסרה מהקמפיין]"
                if suffix not in existing:
                    c.mentor_feedback = existing + suffix
                c.save()

        count = assignments.count()
        assignments.delete()
        return count

