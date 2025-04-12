from django.test import TestCase
from django.contrib.auth.models import User
from mentorApp.models import Mentor, MentorGroup
from childApp.models import Child
from mentorApp.utils.MentorGroupUtils import MentorGroupUtils


class MentorGroupUtilsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='mentor_user')
        self.mentor = Mentor.objects.create(user=self.user, available_teencoins=100)

        self.group1 = MentorGroup.objects.create(
            mentor=self.mentor,
            name="Math Group",
            description="Algebra & Geometry",
            is_active=True
        )
        self.group2 = MentorGroup.objects.create(
            mentor=self.mentor,
            name="Science Group",
            description="Physics and Chemistry",
            is_active=False
        )

        self.child1 = Child.objects.create(
            user=User.objects.create(username='child1'),
            points=10,
            identifier='A001',
            secret_code='123'
        )
        self.child2 = Child.objects.create(
            user=User.objects.create(username='child2'),
            points=20,
            identifier='A002',
            secret_code='456'
        )

        self.group1.children.add(self.child1)
        self.group2.children.add(self.child1, self.child2)

    def test_get_groups_for_mentor_all(self):
        groups = MentorGroupUtils.get_groups_for_mentor(self.mentor)
        self.assertEqual(set(groups), {self.group1, self.group2})

    def test_get_groups_for_mentor_active_only(self):
        groups = MentorGroupUtils.get_groups_for_mentor(self.mentor, active_only=True)
        self.assertEqual(list(groups), [self.group1])

    def test_get_groups_for_mentor_with_search_query(self):
        groups = MentorGroupUtils.get_groups_for_mentor(self.mentor, search_query='Physics')
        self.assertEqual(list(groups), [self.group2])

    def test_get_group_children(self):
        children = MentorGroupUtils.get_group_children(self.group2)
        self.assertEqual(set(children), {self.child1, self.child2})

    def test_get_total_points_for_group(self):
        total_points = MentorGroupUtils.get_total_points_for_group(self.group2)
        self.assertEqual(total_points, 30)

    def test_assign_children_to_group(self):
        MentorGroupUtils.assign_children_to_group(self.group1, [self.child2])
        children = list(self.group1.children.all())
        self.assertEqual(children, [self.child2])

    def test_remove_child_from_all_groups(self):
        # child1 is in both group1 and group2
        MentorGroupUtils.remove_child_from_all_groups(self.child1, self.mentor)
        self.assertFalse(self.group1.children.filter(id=self.child1.id).exists())
        self.assertFalse(self.group2.children.filter(id=self.child1.id).exists())

    def test_count_active_groups_for_mentor(self):
        count = MentorGroupUtils.count_active_groups_for_mentor(self.mentor)
        self.assertEqual(count, 1)

    def test_has_access_to_group_true(self):
        access = MentorGroupUtils.has_access_to_group(self.group1, self.mentor)
        self.assertTrue(access)

    def test_has_access_to_group_false(self):
        other_user = User.objects.create(username='other')
        other_mentor = Mentor.objects.create(user=other_user, available_teencoins=50)
        access = MentorGroupUtils.has_access_to_group(self.group1, other_mentor)
        self.assertFalse(access)
