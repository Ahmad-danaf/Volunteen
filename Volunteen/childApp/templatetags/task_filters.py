from django import template
register = template.Library()

@register.filter
def filter_by_status(tasks, status):
    return [task for task in tasks if (task.status or 'not_started') == status]
