from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone

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
        # Lock campaign row to prevent race conditions
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)

        # 1. Already joined & slot still valid?
        if CampaignUtils.current_approved_children_qs(campaign).filter(child=child.pk).exists():
            raise ValueError("Child already joined this campaign.")

        # 2. Check capacity
        current_slots = CampaignUtils.current_approved_children_qs(campaign).count()
        if campaign.max_children and current_slots >= campaign.max_children:
            raise ValueError("Campaign is full.")

        # 3. Bulk‑assign tasks
        mentor = CampaignUtils.get_campaign_mentor()
        assignments = [
            TaskAssignment(
                child=child,
                task=task,
                assigned_by=mentor.user,   # existing FK on TaskAssignment
                # assigned_at auto_now_add already set
            )
            for task in campaign.tasks.all()
        ]
        TaskAssignment.objects.bulk_create(assignments, ignore_conflicts=True)

        return len(assignments)  # how many tasks were linked


    @staticmethod
    def expire_campaign_reservations(minutes: int = CAMPAIGN_TIME_LIMIT_MINUTES) -> int:
        """
        Release all campaign slots that are either:
        - older than *minutes* without mentor approval,
        - or have any rejected TaskCompletion.
        Returns the number of TaskAssignments deleted.
        """
        cutoff = timezone.now() - timedelta(minutes=minutes)

        # Children+tasks with a rejected completion
        rejected_pairs = TaskCompletion.objects.filter(
            status="rejected"
        ).values_list("child", "task")

        # Build a Q for any TaskAssignment matching those pairs
        rejected_q = Q()
        for child_id, task_id in rejected_pairs:
            rejected_q |= Q(child_id=child_id, task_id=task_id)

        qs = TaskAssignment.objects.filter(
            task__campaign__isnull=False
        ).filter(
            Q(assigned_at__lt=cutoff) | rejected_q
        )

        affected = qs.count()
        qs.delete()
        return affected
    
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
