# managementApp/tests/utils/test_campaign_utils.py
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from childApp.models import Child
from mentorApp.models import Mentor
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from shopApp.models import Shop, Campaign
from childApp.utils.CampaignUtils import CampaignUtils
from Volunteen.constants import CAMPAIGN_TIME_LIMIT_MINUTES,CAMPAIGN_MENTOR_USERNAME

User = get_user_model()


# ----------------------------------------------------------------------
# Helper factory
# ----------------------------------------------------------------------
def _make_child(username: str) -> Child:
    u = User.objects.create(username=username)
    return Child.objects.create(
        user=u,
        identifier=username[:5],
        secret_code=username[:3],
    )


class CampaignUtilsTests(TestCase):
    """Full coverage for CampaignUtils."""

    def setUp(self):
        self.manager = User.objects.create(username="mgr")
        self.shop = Shop.objects.create(user=self.manager, name="Shop")
        self.campaign = Campaign.objects.create(
            shop=self.shop,
            title="Camp",
            description="",
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=7),
            is_active=True,
            max_children=10,          
        )
        # two tasks
        self.task1 = Task.objects.create(
            title="T1", description="x", points=5,
            deadline=timezone.localdate() + timedelta(days=3),
            campaign=self.campaign,
        )
        self.task2 = Task.objects.create(
            title="T2", description="x", points=5,
            deadline=timezone.localdate() + timedelta(days=3),
            campaign=self.campaign,
        )

        self.mentor = CampaignUtils.get_campaign_mentor()

    # ------------------------------------------------------------------
    # 1. get_campaign_mentor idempotent
    # ------------------------------------------------------------------
    def test_get_campaign_mentor_idempotent(self):
        m2 = CampaignUtils.get_campaign_mentor()
        self.assertEqual(self.mentor.id, m2.id)
        self.assertFalse(m2.user.is_active)

    # ------------------------------------------------------------------
    # 2. join_campaign and slot limit
    # ------------------------------------------------------------------
    def test_join_campaign_success_and_limit(self):
        # Narrow capacity to 2 *only* for this scenario
        self.campaign.max_children = 2
        self.campaign.save(update_fields=["max_children"])

        c1 = _make_child("kid1")
        c2 = _make_child("kid2")
        c3 = _make_child("kid3")

        # first two succeed
        self.assertEqual(CampaignUtils.join_campaign(c1, self.campaign), 2)
        self.assertEqual(CampaignUtils.join_campaign(c2, self.campaign), 2)

        # third attempt exceeds limit
        with self.assertRaises(ValueError):
            CampaignUtils.join_campaign(c3, self.campaign)

        # duplicate join also forbidden
        with self.assertRaises(ValueError):
            CampaignUtils.join_campaign(c1, self.campaign)

    # ------------------------------------------------------------------
    # 3. child_has_joined / child_has_finished / get_time_left
    # ------------------------------------------------------------------
    def test_child_status_helpers(self):
        kid = _make_child("kidA")
        CampaignUtils.join_campaign(kid, self.campaign)
        self.assertTrue(CampaignUtils.child_has_joined(kid, self.campaign))

        # approve only one task
        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")
        self.assertFalse(CampaignUtils.child_has_finished(kid, self.campaign))

        # approve second task
        TaskCompletion.objects.create(child=kid, task=self.task2, status="approved")
        self.assertTrue(CampaignUtils.child_has_finished(kid, self.campaign))

        # time left should be positive initially
        tl = CampaignUtils.get_time_left(kid, self.campaign)
        self.assertGreater(tl, timedelta())

    # ------------------------------------------------------------------
    # 4. current_approved_children_qs logic
    # ------------------------------------------------------------------
    def test_current_approved_children_qs(self):
        kid_ok = _make_child("kidOK")          # completes all in time
        kid_rej = _make_child("kidRej")        # has rejection
        kid_time = _make_child("kidTime")      # times out

        # join all
        for kid in (kid_ok, kid_rej, kid_time):
            CampaignUtils.join_campaign(kid, self.campaign)

        # approve all for kid_ok
        for t in (self.task1, self.task2):
            TaskCompletion.objects.create(child=kid_ok, task=t, status="approved")

        # kid_rej -> one rejected
        TaskCompletion.objects.create(child=kid_rej, task=self.task1, status="rejected")

        # kid_time -> no completions, but fast-forward assignment time
        old = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES + 5)
        TaskAssignment.objects.filter(child=kid_time).update(assigned_at=old)

        ids = set(
            CampaignUtils.current_approved_children_qs(self.campaign)
            .values_list("child_id", flat=True)
        )
        self.assertSetEqual(ids, {kid_ok.id})   # only kid_ok keeps slot

    # ------------------------------------------------------------------
    # 5. expire_campaign_reservations return value & effect
    # ------------------------------------------------------------------
    def test_expire_campaign_reservations(self):
        kid_incomplete = _make_child("kidInc")
        kid_complete = _make_child("kidFull")
        kid_rejected = _make_child("kidBad")

        for kid in (kid_incomplete, kid_complete, kid_rejected):
            CampaignUtils.join_campaign(kid, self.campaign)

        # kid_complete finishes
        for t in (self.task1, self.task2):
            TaskCompletion.objects.create(child=kid_complete, task=t, status="approved")

        # kid_rejected – mark one rejected
        TaskCompletion.objects.create(child=kid_rejected, task=self.task1, status="rejected")

        # kid_incomplete times out
        old = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES + 2)
        TaskAssignment.objects.filter(child=kid_incomplete).update(assigned_at=old)

        # run expiry
        deleted = CampaignUtils.expire_campaign_reservations()

        # kid_incomplete & kid_rejected each had 2 assignments => 4 deleted
        self.assertEqual(deleted, 4)

        remaining_ids = set(
            TaskAssignment.objects.filter(task__campaign=self.campaign)
            .values_list("child_id", flat=True)
        )
        self.assertSetEqual(remaining_ids, {kid_complete.id})

    # ------------------------------------------------------------------
    # 6. leave_campaign & clear completions
    # ------------------------------------------------------------------
    def test_leave_campaign(self):
        kid = _make_child("kidQuit")
        CampaignUtils.join_campaign(kid, self.campaign)
        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")

        deleted = CampaignUtils.leave_campaign(kid, self.campaign)
        # two assignments removed
        self.assertEqual(deleted, 2)
        self.assertFalse(TaskAssignment.objects.filter(child=kid).exists())
        self.assertFalse(TaskCompletion.objects.filter(child=kid).exists())
        
    # ------------------------------------------------------------------
    # 7. get_child_join_date & get_time_left edge-cases
    # ------------------------------------------------------------------
    def test_join_date_and_time_left_none_when_not_joined(self):
        stranger = _make_child("stranger")
        self.assertIsNone(CampaignUtils.get_child_join_date(stranger, self.campaign))
        self.assertIsNone(CampaignUtils.get_time_left(stranger, self.campaign))

    def test_get_child_join_date_returns_first_assignment_time(self):
        kid = _make_child("kidJoinDate")
        CampaignUtils.join_campaign(kid, self.campaign)
        first = TaskAssignment.objects.filter(child=kid).order_by("assigned_at").first().assigned_at
        self.assertEqual(CampaignUtils.get_child_join_date(kid, self.campaign), first)

    # ------------------------------------------------------------------
    # 8. clear_campaign_completions deletes only completions
    # ------------------------------------------------------------------
    def test_clear_campaign_completions(self):
        kid = _make_child("kidClear")
        CampaignUtils.join_campaign(kid, self.campaign)
        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")
        deleted = CampaignUtils.clear_campaign_completions(kid, self.campaign)
        self.assertEqual(deleted, 1)
        # assignments still exist
        self.assertTrue(TaskAssignment.objects.filter(child=kid).exists())
        # completions deleted
        self.assertFalse(TaskCompletion.objects.filter(child=kid).exists())

    # ------------------------------------------------------------------
    # 9. expire_campaign_reservations when campaign has no tasks / inactive
    # ------------------------------------------------------------------
    def test_expire_campaign_no_tasks_or_inactive(self):
        empty_camp = Campaign.objects.create(
            shop=self.shop,
            title="Empty", start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=3),
            is_active=True,
        )
        inactive_camp = Campaign.objects.create(
            shop=self.shop,
            title="Inactive", start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=3),
            is_active=False,
        )
        self.assertEqual(CampaignUtils.expire_campaign_reservations(), 0)

    # ------------------------------------------------------------------
    # 10. join_campaign assigns exactly all campaign tasks
    # ------------------------------------------------------------------
    def test_join_campaign_assignment_count_matches_task_count(self):
        kid = _make_child("kidCount")
        num = CampaignUtils.join_campaign(kid, self.campaign)
        self.assertEqual(num, self.campaign.tasks.count())
        self.assertEqual(
            TaskAssignment.objects.filter(child=kid, task__campaign=self.campaign).count(),
            self.campaign.tasks.count()
        )

    # ------------------------------------------------------------------
    # 11. join_campaign concurrent race condition
    # ------------------------------------------------------------------
    def test_join_campaign_concurrent_race_condition(self):
        self.campaign.max_children = 1
        self.campaign.save()

        kid1 = _make_child("k1")
        kid2 = _make_child("k2")

        # Force kid1 to join first
        CampaignUtils.join_campaign(kid1, self.campaign)

        # Try kid2 — should raise due to limit reached
        with self.assertRaises(ValueError):
            CampaignUtils.join_campaign(kid2, self.campaign)
            
    # ------------------------------------------------------------------
    # 12. test_expire_campaign_reservations_deletes_uncompleted_after_timeout
    # ------------------------------------------------------------------
    def test_expire_campaign_reservations_deletes_uncompleted_after_timeout(self):
        kid = _make_child("timeout")
        CampaignUtils.join_campaign(kid, self.campaign)

        old_time = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES + 1)
        TaskAssignment.objects.filter(child=kid).update(assigned_at=old_time)

        deleted = CampaignUtils.expire_campaign_reservations()
        self.assertEqual(deleted, 2)  # 2 tasks assigned
        
    # ------------------------------------------------------------------
    # 13. clear_campaign_completions_no_entries
    # ------------------------------------------------------------------
    def test_clear_campaign_completions_no_entries(self):
        kid = _make_child("noclear")
        CampaignUtils.join_campaign(kid, self.campaign)

        deleted = CampaignUtils.clear_campaign_completions(kid, self.campaign)
        self.assertEqual(deleted, 0)

    # ------------------------------------------------------------------
    # 14. get_time_left_boundary_zero
    # ------------------------------------------------------------------
    def test_get_time_left_boundary_zero(self):
        kid = _make_child("kbound")
        CampaignUtils.join_campaign(kid, self.campaign)

        # Force assignment to be exactly at the cutoff time
        cutoff = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES)
        TaskAssignment.objects.filter(child=kid).update(assigned_at=cutoff)

        tl = CampaignUtils.get_time_left(kid, self.campaign)
        self.assertEqual(tl, timedelta(seconds=0))
        
    # ------------------------------------------------------------------
    # 15. child_has_finished_zero_tasks
    # ------------------------------------------------------------------
    def test_child_has_finished_zero_tasks(self):
        empty_camp = Campaign.objects.create(
            shop=self.shop,
            title="Empty",
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + timedelta(days=3),
            is_active=True,
        )
        kid = _make_child("noTasksKid")
        self.assertFalse(CampaignUtils.child_has_finished(kid, empty_camp))

    # ------------------------------------------------------------------
    # 16. child_has_joined_false_if_no_assignment
    # ------------------------------------------------------------------
    def test_child_has_joined_false_if_no_assignment(self):
        kid = _make_child("ghostJoin")
        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")
        self.assertFalse(CampaignUtils.child_has_joined(kid, self.campaign))

    # ------------------------------------------------------------------
    # 17. join_campaign_clears_old_completions
    # ------------------------------------------------------------------
    def test_join_campaign_clears_old_completions(self):
        kid = _make_child("rejoinKid")

        # Simulate old completions before rejoin
        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")
        TaskCompletion.objects.create(child=kid, task=self.task2, status="approved")

        # Then rejoin
        CampaignUtils.join_campaign(kid, self.campaign)

        # Old completions should be cleared
        self.assertFalse(TaskCompletion.objects.filter(child=kid, task__campaign=self.campaign).exists())

    # ------------------------------------------------------------------
    # 18. expire_campaign_partial_completion_timed_out
    # ------------------------------------------------------------------
    def test_expire_campaign_partial_completion_timed_out(self):
        kid = _make_child("partial")
        CampaignUtils.join_campaign(kid, self.campaign)

        TaskCompletion.objects.create(child=kid, task=self.task1, status="approved")
        timeout = timezone.localtime(timezone.now()) - timedelta(minutes=CAMPAIGN_TIME_LIMIT_MINUTES + 2)
        TaskAssignment.objects.filter(child=kid).update(assigned_at=timeout)

        deleted = CampaignUtils.expire_campaign_reservations()
        self.assertEqual(deleted, 2)

    # ------------------------------------------------------------------
    # 19. get_campaign_mentor_uniqueness
    # ------------------------------------------------------------------
    def test_get_campaign_mentor_uniqueness(self):
        CampaignUtils.get_campaign_mentor()
        CampaignUtils.get_campaign_mentor()
        self.assertEqual(Mentor.objects.filter(user__username=CAMPAIGN_MENTOR_USERNAME).count(), 1)
