from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import (
    OuterRef, Subquery, Exists,
    Count, F, Min, Q, DateTimeField, ExpressionWrapper
)
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone
from django.db import models
from childApp.models import Child
from mentorApp.models import Mentor                     
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from shopApp.models import Campaign                    
from Volunteen.constants import CAMPAIGN_MENTOR_USERNAME, CAMPAIGN_TIME_LIMIT_MINUTES, CAMPAIGN_BAN_DURATION_HOURS
from django.utils.translation import gettext as _

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
        Children who *still* hold a valid slot:
        - Either completed all campaign tasks with approval
        - OR are still within the time window and have no rejected completions
        """
        cutoff = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES)

        # Exclude anyone with rejected task
        rejected_children = TaskCompletion.objects.filter(
            task__campaign=campaign,
            status="rejected"
        ).values_list("child_id", flat=True)

        #  Children who completed *all* tasks with approval
        approved_children = TaskCompletion.objects.filter(
            task__campaign=campaign,
            status="approved"
        ).values("child_id").annotate(
            approved_count=Count("task_id", distinct=True)
        ).filter(approved_count=campaign.tasks.count()).exclude(child_id__in=rejected_children)

        # Children who are still within time window (assigned_at >= cutoff)
        active_assignments = TaskAssignment.objects.filter(
            task__campaign=campaign,
            assigned_at__gte=cutoff,
            refunded_at__isnull=True
        ).exclude(child_id__in=rejected_children).values("child_id").distinct()

        # Union of both groups
        approved_ids = set([row["child_id"] for row in approved_children])
        active_ids = set([row["child_id"] for row in active_assignments])
        valid_ids = approved_ids | active_ids

        return TaskAssignment.objects.filter(
            task__campaign=campaign,
            child_id__in=valid_ids
        ).values("child_id").distinct()
        
    @staticmethod
    @transaction.atomic
    def join_campaign(child: Child, campaign: Campaign):
        """
        Reserve a slot and assign every task in the campaign to *child*.

        Raises:
            ValueError – if limit reached or child already holds an active slot.
        """
        campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
        CampaignUtils.clear_campaign_completions(child, campaign)
        if child.campaign_ban_until and timezone.localtime(timezone.now()) < child.campaign_ban_until:
            raise ValueError(_(f"לא ניתן להצטרף לקמפיין כעת. נסה שוב בעוד {CAMPAIGN_BAN_DURATION_HOURS} שעות."))
        if CampaignUtils.current_approved_children_qs(campaign).filter(child=child.pk).exists():
            raise ValueError(_("את/ה כבר נרשמת לקמפיין זה."))

        current_slots = CampaignUtils.current_approved_children_qs(campaign).count()
        if campaign.max_children and current_slots >= campaign.max_children:
            raise ValueError(_("הקמפיין מלא."))

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
    @transaction.atomic
    def expire_campaign_reservations(
        minutes: int = CAMPAIGN_TIME_LIMIT_MINUTES
    ) -> int:
        """
        Expire campaign slots globally.

        Rules
        -----
        1. *Reject* rule – any `rejected` completion → lose slot immediately.
        2. *Timeout* rule – if first assignment is older than *minutes* **and**
            not every task is mentor-approved.

        Returns
        -------
        int
            Number of TaskAssignments deleted.
        """
        now = timezone.localtime(timezone.now())
        cutoff = now - timedelta(minutes=minutes)

        deleted_total = 0

        for camp in Campaign.objects.filter(is_active=True).prefetch_related("tasks"):
            tasks_qs = camp.tasks.all()
            total_tasks = tasks_qs.count()
            if total_tasks == 0:
                continue

            # Subquery: Does child have *any* rejected completion
            rejected_exists = Exists(
                TaskCompletion.objects.filter(
                    child_id=OuterRef("child_id"),
                    task__campaign=camp,
                    status="rejected")
            )

            # Subquery: Count approved tasks for child in this campaign
            approved_cnt = (
                TaskCompletion.objects
                .filter(
                    child_id=OuterRef("child_id"),
                    task__campaign=camp,
                    status="approved")
                .values("child_id")
                .annotate(cnt=Count("task_id", distinct=True))
                .values("cnt")
            )

            # For each child w/ assignments in this campaign choose
            # min(assigned_at) once.
            child_info = (
                TaskAssignment.objects
                .filter(task__campaign=camp)
                .values("child_id")
                .annotate(first_assigned=Min("assigned_at"))
                .annotate(rejected=rejected_exists)
                .annotate(approved_all=Subquery(approved_cnt))
            )

            # Build list of child_ids to expire (reject OR timeout+incomplete)
            to_expire_ids = [
                row["child_id"]
                for row in child_info
                if (
                    row["rejected"] or (
                        row["first_assigned"] < cutoff and
                        (row["approved_all"] or 0) < total_tasks
                    )
                )
            ]

            if not to_expire_ids:
                continue

            # Delete TaskCompletions first
            comps_qs = TaskCompletion.objects.filter(
                child_id__in=to_expire_ids,
                task__campaign=camp,
            )
            comps_qs.delete()

            # Delete assignments (and count them)
            assign_qs = TaskAssignment.objects.filter(
                child_id__in=to_expire_ids,
                task__campaign=camp,
            )
            deleted_total += assign_qs.count()
            assign_qs.delete()

        return deleted_total

    
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
        
        CampaignUtils.clear_campaign_completions(child, campaign)

        count = assignments.count()
        assignments.delete()
        child.campaign_ban_until = timezone.localtime(timezone.now()) + timedelta(hours=CAMPAIGN_BAN_DURATION_HOURS)
        child.save()
        return count


    @staticmethod
    def get_child_join_date(child: Child, campaign: Campaign):
        """
        Returns the date and time the child joined the campaign.
        """
        try:
            assignment = TaskAssignment.objects.filter(
                child=child,
                task__campaign=campaign
            ).order_by("assigned_at").first()
            return assignment.assigned_at if assignment else None
        except TaskAssignment.DoesNotExist:
            return None
        
        
    @staticmethod
    @transaction.atomic
    def clear_campaign_completions(child: Child, campaign: Campaign) -> int:
        """
        Deletes all TaskCompletions for a child in a given campaign.
        This is useful for allowing a second chance to rejoin the campaign.
        Returns the number of completions deleted.
        """
        qs = TaskCompletion.objects.filter(
            child=child,
            task__campaign=campaign
        )
        deleted_count = qs.count()
        qs.delete()
        return deleted_count

    @staticmethod
    def is_campaign_banned(child: Child) -> bool:
        """
        Returns True if the child is banned from joining campaigns.
        """
        return child.campaign_ban_until and timezone.localtime(timezone.now()) < child.campaign_ban_until

