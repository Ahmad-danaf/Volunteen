from django.core.management.base import BaseCommand
from teenApp.entities.task import Task
from childApp.models import Child
from teenApp.entities.TaskAssignment import TaskAssignment
from django.utils import timezone
from datetime import datetime

class Command(BaseCommand):
    help = 'Assigns Task.assigned_children field based on TaskAssignment model'

    def handle(self, *args, **kwargs):
        today_start = timezone.make_aware(datetime.combine(timezone.now().date(), datetime.min.time()))

        # Filter tasks with deadline from today onward
        tasks = Task.objects.filter(deadline__gte=today_start)

        if not tasks.exists():
            self.stdout.write(self.style.WARNING('No tasks found with deadline today or in the future.'))
            return

        for task in tasks:
            # Get all children assigned to this task through TaskAssignment
            assigned_children_qs = TaskAssignment.objects.filter(task=task).values_list('child_id', flat=True).distinct()
            if assigned_children_qs.exists():
                task.assigned_children.set(assigned_children_qs)
                self.stdout.write(self.style.SUCCESS(
                    f'Updated Task: {task.title} with {assigned_children_qs.count()} assigned children.'
                ))
            else:
                task.assigned_children.clear()
                self.stdout.write(self.style.WARNING(
                    f'Cleared assigned children for Task: {task.title}'
                ))

        self.stdout.write(self.style.SUCCESS('All tasks have been updated based on TaskAssignment.'))
