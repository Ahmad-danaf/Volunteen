from django.shortcuts import get_object_or_404
from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion
from mentorApp.forms import TaskForm
from childApp.models import Child
from teenApp.utils.NotificationManager import NotificationManager
from django.db.models import Sum, F, IntegerField

class MentorTaskManager:
    @staticmethod
    def add_task(request, mentor, task_id=None, duplicate=False):
        """
        Create a new task or duplicate an existing one.
        Returns either a Task instance (if creation is successful) or a TaskForm (with errors).
        """
        task = None
        if task_id:
            original_task = get_object_or_404(Task, id=task_id)
            if duplicate:
                # Create a duplicate task instance without saving immediately.
                task = Task(
                    title=f"{original_task.title} (Copy)",
                    description=original_task.description,
                    points=original_task.points,
                    deadline=original_task.deadline,
                    additional_details=original_task.additional_details,
                    img=original_task.img,
                )
        if request.method == 'POST':
            form_instance = None if duplicate else task
            form = TaskForm(mentor=mentor, data=request.POST, instance=form_instance)
            if form.is_valid():
                new_task = form.save(commit=False)
                new_task.save()
                new_task.assigned_mentors.add(mentor)
                form.save_m2m()
                return new_task  # Task created successfully.
            else:
                return form  # Return form with errors.
        else:
            form = TaskForm(mentor=mentor, instance=task)
            return form

    @staticmethod
    def assign_task(task, mentor, children_ids):
        """
        Assign a task to a list of children. This method:
        - Links children to the task.
        - Creates task assignment records.
        - Sends notifications to each child.
        """
        for child_id in children_ids:
            child = get_object_or_404(Child, id=child_id)
            task.assigned_children.add(child)
            # Create assignment record here (if using a TaskAssignment model).
            # TaskAssignment.objects.create(task=task, child=child, is_new=True)
            # Send notifications.
            if child.user.email:
                NotificationManager.sent_mail(
                    f"Dear {child.user.first_name}, a new task '{task.title}' has been assigned to you. Please check and complete it by {task.deadline}.",
                    child.user.email
                )
            if child.user.phone:
                msg = (
                    f"🎉💥 Hey {child.user.username}, you have a new task '{task.title}' worth {task.points} TeenCoins! "
                    "Log in now to see the details."
                )
                NotificationManager.sent_whatsapp(msg, str(child.user.phone))
        task.assigned_mentors.add(mentor)
        return True

    @staticmethod
    def assign_bonus_points(task, child, bonus_points, mentor):
        """
        Process bonus point assignment for a child's task completion.
        Validates bonus points and updates the TaskCompletion record.
        """
        if bonus_points > 10:
            raise ValueError("Maximum of 10 bonus points per assignment is allowed.")
        # Assign bonus points and update task completion.
        task_completion = TaskCompletion.objects.filter(task=task, child=child).first()
        if task_completion:
            task_completion.bonus_points = bonus_points
            task_completion.save()
        # Additional logic can be added here.
        return True

    @staticmethod
    def review_task_completion(task_ids, action):
        """
        Review one or more task completions by approving or rejecting them.
        Returns the count of processed tasks.
        """
        processed = 0
        for task_id in task_ids:
            task_completion = get_object_or_404(TaskCompletion, id=task_id)
            if task_completion.status != 'pending':
                continue
            if action == 'approve':
                task_completion.status = 'approved'
                task_completion.task.approve_task(task_completion.child)
            elif action == 'reject':
                task_completion.status = 'rejected'
            task_completion.save()
            processed += 1
        return processed

    @staticmethod
    def calculate_dashboard_metrics(mentor):
        """
        Calculate overall metrics for the mentor's dashboard.
        Returns a dictionary with total tasks, completed tasks, open tasks, and efficiency rates.
        """
        tasks = Task.objects.filter(assigned_mentors=mentor)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(completed=True).count()
        open_tasks = total_tasks - completed_tasks
        efficiency_rate = round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0

        # Calculate children-specific performance details.
        children_details = []
        for child in mentor.children.all():
            completed = TaskCompletion.objects.filter(child=child, task__in=tasks).count()
            assigned_tasks = tasks.filter(assigned_children=child).count()
            efficiency = round((completed / assigned_tasks) * 100, 2) if assigned_tasks > 0 else 0
            performance_color = "#d4edda" if efficiency >= 75 else "#f8d7da" if efficiency < 50 else "#fff3cd"
            children_details.append({
                'child': child,
                'efficiency_rate': efficiency,
                'performance_color': performance_color,
            })

        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'open_tasks': open_tasks,
            'efficiency_rate': efficiency_rate,
            'children_details': children_details,
        }

    @staticmethod
    def load_children_for_task(task_id):
        """
        Retrieve a list of children who have completed a specific task.
        Useful for AJAX endpoints.
        """
        children = Child.objects.filter(
            taskcompletion__task_id=task_id
        ).order_by('user__username')
        return children
