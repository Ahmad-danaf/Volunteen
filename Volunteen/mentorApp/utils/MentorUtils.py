from django.db.models import Q

class MentorUtils:
    
    @staticmethod
    def get_children_for_mentor(mentor, search_query=''):
        """
        Return all Children belonging to a given mentor, optionally filtered by a search query.
        The search query will match username, first_name, or last_name.
        """
        children = mentor.children.all()
        if search_query:
            children = children.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )
        return children
    
