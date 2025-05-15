from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from teenApp.utils import referral_utils
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from mentorApp.models import Mentor
from childApp.utils.CampaignUtils import CampaignUtils
from parentApp.models import ChildSubscription

class ReferralTaskFlowTest(TestCase):
    def setUp(self):
        # Create mentor and override CampaignUtils
        self.mentor_user = User.objects.create(username="mentor")
        self.mentor = Mentor.objects.create(user=self.mentor_user)
        CampaignUtils.get_campaign_mentor = lambda: self.mentor

        # Create 5 children with active subscriptions
        self.children = []
        for i in range(5):
            username = f"child{i}"
            user = User.objects.create(username=f"child{i}")
            child = Child.objects.create(user=user,
                                        identifier=f"{i:05}"[-3:].zfill(5),
                                        secret_code=username[:3]
                                        )
            start = timezone.now().date() - timedelta(days=3)
            end = timezone.now().date() + timedelta(days=30)
            subscription = ChildSubscription.objects.create(
                child=child,
                plan=ChildSubscription.Plan.MONTHLY,
                start_date=start,
                end_date=end,
                status=ChildSubscription.Status.ACTIVE,
            )
            child.save()
            self.mentor.children.add(child)
            self.children.append(child)

    def simulate_day(self, days_ahead=0):
        return referral_utils.recreate_referral_tasks_for_all()

    def test_referral_task_lifecycle(self):
        # Day 0: assign all
        result = self.simulate_day(0)
        self.assertIn("Assigned 5 children", result)
        self.assertEqual(Task.objects.count(), 1)

        task1 = Task.objects.first()

        # Day 1: Child 0 completes
        TaskCompletion.objects.create(child=self.children[0], task=task1, status="approved")
        result = self.simulate_day(1)
        self.assertTrue(
            TaskAssignment.objects.filter(child=self.children[0]).count() == 2,
            "Child 0 should have 2 assignments (reassigned)"
        )
        self.assertTrue(
            TaskAssignment.objects.filter(child=self.children[1]).count() == 1,
            "Child 1 should still have only 1 assignment"
        )

        # Day 2: Child 1 completes
        TaskCompletion.objects.create(child=self.children[1], task=task1, status="approved")
        result = self.simulate_day(2)
        self.assertTrue(
            TaskAssignment.objects.filter(child=self.children[1]).count() == 2,
            "Child 1 should now have 2 assignments"
        )

        # Day 7: task expires
        task1.deadline = timezone.now().date() - timedelta(days=1)
        task1.save()

        result = self.simulate_day(8)
        self.assertIn("Assigned 5 children", result)
        self.assertEqual(Task.objects.count(), 2)

        task2 = Task.objects.exclude(id=task1.id).first()
        for child in self.children:
            self.assertTrue(TaskAssignment.objects.filter(child=child, task=task2).exists())

        # Day 9–10: No new tasks needed
        result = self.simulate_day(9)
        self.assertIn("No referral task needed", result)
        result = self.simulate_day(10)
        self.assertIn("No referral task needed", result)

        print("All referral lifecycle use cases passed.")
