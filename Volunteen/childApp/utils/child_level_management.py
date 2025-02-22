from django.db.models import Sum, F, Case, When, Value, IntegerField
from teenApp.entities.TaskCompletion import TaskCompletion
def calculate_total_points(child):
    """
    Calculate the total points a child has earned from completed tasks.
    Points are based on task points + bonus points from TaskCompletion records.
    Only includes tasks with status 'approved'.
    """
    total_points = TaskCompletion.objects.filter(
        child=child,
        status='approved'  # Filter only approved tasks
    ).aggregate(
        total_points=Sum(
            F('task__points') + F('bonus_points'),
            output_field=IntegerField()
        )
    )['total_points']
    return total_points or 0
