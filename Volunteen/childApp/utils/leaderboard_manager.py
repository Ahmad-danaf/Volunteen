from django.db.models import Sum, Case, When, Value, IntegerField, F
from childApp.models import Child
from teenApp.entities.TaskCompletion import TaskCompletion

def get_top_children(limit=None, start_date=None, end_date=None):
    """ Returns a list of children ranked by the number of points in descending order """
    
    children = Child.objects.all()

    if start_date and end_date:
        children = children.annotate(
            task_points_within_range=Sum(
                Case(
                    When(
                        taskcompletion__completion_date__range=(start_date, end_date),
                        taskcompletion__status='approved',
                        then=F('taskcompletion__task__points') + F('taskcompletion__bonus_points')
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).order_by('-task_points_within_range')
    else:
        children = children.annotate(
            total_points=Sum(
                Case(
                    When(
                        taskcompletion__status='approved',
                        then=F('taskcompletion__task__points') + F('taskcompletion__bonus_points')
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).order_by('-total_points')

    return children[:limit] if limit else children  # מגביל ל-TOP 3 אם צריך
