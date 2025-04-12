from django.test import TestCase
from django.contrib.auth.models import User
from mentorApp.models import Mentor
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from mentorApp.utils.MentorUtils import MentorUtils


class MentorUtilsTest(TestCase):
    def setUp(self):
        self.mentor_user = User.objects.create(username='mentor')
        self.mentor = Mentor.objects.create(user=self.mentor_user, available_teencoins=100)

        self.child1_user = User.objects.create(username='child_one', first_name='Ali', last_name='Ahmad')
        self.child1 = Child.objects.create(user=self.child1_user, identifier='C001', secret_code='123')
        self.child1.mentors.add(self.mentor)

        self.child2_user = User.objects.create(username='child_two', first_name='Zayn', last_name='Omar')
        self.child2 = Child.objects.create(user=self.child2_user, identifier='C002', secret_code='456')
        self.child2.mentors.add(self.mentor)

        self.task = Task.objects.create(
            title='Test Task',
            description='Task description',
            points=10,
            deadline='2099-12-31'
        )
        self.task.assigned_mentors.add(self.mentor)

        TaskAssignment.objects.create(task=self.task, child=self.child1, assigned_by=self.mentor.user)
        TaskAssignment.objects.create(task=self.task, child=self.child2, assigned_by=self.mentor.user)

        TaskCompletion.objects.create(task=self.task, child=self.child1, status='approved', bonus_points=2)
        TaskCompletion.objects.create(task=self.task, child=self.child2, status='pending', bonus_points=0)

    def test_get_children_for_mentor_without_search(self):
        result = MentorUtils.get_children_for_mentor(self.mentor)
        self.assertEqual(set(result), {self.child1, self.child2})

    def test_get_children_for_mentor_with_search(self):
        result = MentorUtils.get_children_for_mentor(self.mentor, search_query='Ali')
        self.assertEqual(list(result), [self.child1])

    def test_get_children_performance_data(self):
        performance = MentorUtils.get_children_performance_data(self.mentor)
        self.assertEqual(len(performance), 2)
        data = {entry['child_name']: entry for entry in performance}
        self.assertEqual(data['child_one']['approved_completions'], 1)
        self.assertEqual(data['child_one']['total_assigned_tasks'], 1)
        self.assertEqual(data['child_two']['approved_completions'], 0)
        self.assertEqual(data['child_two']['total_assigned_tasks'], 1)
