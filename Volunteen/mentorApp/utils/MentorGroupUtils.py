from django.db.models import Q
from mentorApp.models import MentorGroup
from childApp.models import Child
from django.db import models


class MentorGroupUtils:
    @staticmethod
    def get_groups_for_mentor(mentor, active_only=False, search_query=''):
        """
        Return all groups for a mentor, with optional filtering by active status and search query.
        """
        groups = MentorGroup.objects.filter(mentor=mentor)

        if active_only:
            groups = groups.filter(is_active=True)

        if search_query:
            groups = groups.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        return groups

    @staticmethod
    def get_group_children(group):
        """
        Return all children in a group.
        """
        return group.children.all()

    @staticmethod
    def get_total_points_for_group(group):
        """
        Return the total points accumulated by all children in a group.
        """
        return group.children.aggregate(total_points=models.Sum('points'))['total_points'] or 0

    @staticmethod
    def assign_children_to_group(group, children_queryset):
        """
        Safely assign children to a group.
        """
        group.children.set(children_queryset)
        group.save()

    @staticmethod
    def remove_child_from_all_groups(child, mentor):
        """
        Remove a specific child from all of the mentor's groups.
        """
        groups = MentorGroup.objects.filter(mentor=mentor, children=child)
        for group in groups:
            group.children.remove(child)

    @staticmethod
    def count_active_groups_for_mentor(mentor):
        """
        Return the number of active groups a mentor has.
        """
        return MentorGroup.objects.filter(mentor=mentor, is_active=True).count()

    @staticmethod
    def has_access_to_group(group, mentor):
        """
        Check if the given group belongs to the mentor.
        """
        return group.mentor == mentor
