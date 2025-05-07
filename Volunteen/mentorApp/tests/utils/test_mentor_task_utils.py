from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from mentorApp.models import Mentor
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils
from datetime import timedelta

class MentorTaskUtilsTest(TestCase):
    def setUp(self):
        self.mentor_user = User.objects.create(username='mentor')
        self.mentor = Mentor.objects.create(user=self.mentor_user, available_teencoins=100)

        self.child_user = User.objects.create(username='child1')
        self.child = Child.objects.create(
            user=self.child_user,
            identifier='A001',
            secret_code='111',
            points=0
        )
        self.child.mentors.add(self.mentor)

        self.task = Task.objects.create(
            title='Test Task',
            description='Do something',
            deadline='2099-12-31',
            points=10
        )
        self.task.assigned_mentors.add(self.mentor)

        self.task_completion = TaskCompletion.objects.create(
            task=self.task,
            child=self.child,
            status='pending',
            bonus_points=5,
            remaining_coins=0
        )

    def test_assign_task_to_child_success(self):
        assignment = MentorTaskUtils.assign_task_to_child(self.mentor, self.task, self.child)
        self.assertEqual(assignment.task, self.task)
        self.assertEqual(assignment.child, self.child)

    def test_assign_task_to_unauthorized_child(self):
        new_user = User.objects.create(username='unauth_child')
        new_child = Child.objects.create(user=new_user, identifier='A002', secret_code='222')
        with self.assertRaises(ValueError):
            MentorTaskUtils.assign_task_to_child(self.mentor, self.task, new_child)

    def test_approve_task_completion_by_mentor(self):
        approved = MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        self.assertEqual(approved.status, 'approved')
        self.assertEqual(approved.remaining_coins, 15)
        self.assertEqual(approved.approved_by, self.mentor_user)

    def test_approve_already_approved_task_raises(self):
        self.task_completion.status = 'approved'
        self.task_completion.save()
        with self.assertRaises(ValueError):
            MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)

    def test_reject_task_completion_by_mentor(self):
        rejected = MentorTaskUtils.reject_task_completion_by_mentor(self.mentor, self.task_completion, feedback="Not good")
        self.assertEqual(rejected.status, 'rejected')
        self.assertEqual(rejected.mentor_feedback, "Not good")

    def test_assign_bonus_success(self):
        self.mentor.available_teencoins = 100
        self.mentor.save()
        updated = MentorTaskUtils.assign_bonus_to_task_completion(self.mentor, self.task_completion.id, 5)
        self.assertEqual(updated.bonus_points, 10)
        self.assertEqual(updated.remaining_coins, 5)

    def test_assign_bonus_not_enough_coins(self):
        self.mentor.available_teencoins = 2
        self.mentor.save()
        with self.assertRaises(ValueError):
            MentorTaskUtils.assign_bonus_to_task_completion(self.mentor, self.task_completion.id, 10)

    def test_get_all_tasks_assigned_to_mentor(self):
        tasks = MentorTaskUtils.get_all_tasks_assigned_to_mentor(self.mentor)
        self.assertIn(self.task, tasks)

    def test_get_mentor_children_with_completed_tasks(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        result = MentorTaskUtils.get_mentor_children_with_completed_tasks(self.mentor)
        self.assertIn(self.child, result)
        self.assertEqual(len(result[self.child]), 1)

    def test_get_template_tasks(self):
        self.task.is_template = True
        self.task.save()
        templates = MentorTaskUtils.get_template_tasks(self.mentor, search_query='test')
        self.assertIn(self.task, templates)

    def test_get_approved_task_completions_for_mentor_and_child(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        completions = MentorTaskUtils.get_approved_task_completions_for_mentor_and_child(self.mentor, self.child)
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0], self.task_completion)

    def test_count_approved_task_completions_for_child_from_mentor(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        count = MentorTaskUtils.count_approved_task_completions_for_child_from_mentor(self.mentor, self.child)
        self.assertEqual(count, 1)

    def test_get_active_tasks_for_child_from_mentor(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        active_tasks = MentorTaskUtils.get_active_tasks_for_child_from_mentor(self.mentor, self.child)
        self.assertEqual(len(active_tasks), 0)

    def test_count_total_assigned_tasks_for_child_from_mentor(self):
        MentorTaskUtils.assign_task_to_child(self.mentor, self.task, self.child)
        count = MentorTaskUtils.count_total_assigned_tasks_for_child_from_mentor(self.mentor, self.child)
        self.assertEqual(count, 1)

    def test_get_mentor_active_tasks(self):
        tasks = MentorTaskUtils.get_mentor_active_tasks(self.mentor)
        self.assertIn(self.task, tasks)

    def test_get_approved_completions_for_task(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        completions = MentorTaskUtils.get_approved_completions_for_task(self.mentor, self.task)
        self.assertEqual(len(completions), 1)

    def test_get_active_completions_for_mentor_child(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        completions = MentorTaskUtils.get_active_completions_for_mentor_child(self.mentor, self.child)
        self.assertTrue(all(c.status == 'approved' for c in completions))

    def test_get_children_with_completed_tasks_for_mentor(self):
        MentorTaskUtils.approve_task_completion_by_mentor(self.mentor, self.task_completion)
        children = MentorTaskUtils.get_children_with_completed_tasks_for_mentor(self.mentor)
        self.assertGreaterEqual(len(children), 1)
        self.assertEqual(children[0].task_total_points, 15)

    def test_create_task_with_assignments_success(self):
        task_data = {
            'title': 'New Task',
            'description': 'Do X',
            'deadline': '2099-12-31',
            'points': 10
        }
        task = MentorTaskUtils.create_task_with_assignments(
            mentor=self.mentor,
            children_ids=[self.child.id],
            task_data=task_data
        )
        self.assertEqual(task.points, 10)
        self.assertEqual(task.assigned_children.count(), 1)
        self.assertEqual(task.assigned_mentors.count(), 1)
        self.mentor.refresh_from_db()
        self.assertEqual(self.mentor.available_teencoins, 90)

