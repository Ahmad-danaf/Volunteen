from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import Task
from childApp.models import Child
from mentorApp.models import Mentor
from teenApp.utils.TaskManagerUtils import TaskManagerUtils
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, F, IntegerField, Prefetch
from Volunteen.constants import TEEN_COINS_EXPIRATION_MONTHS
from dateutil.relativedelta import relativedelta
from django_q.tasks import async_task
from teenApp.utils.NotificationManager import NotificationManager
import hashlib

class MentorTaskUtils(TaskManagerUtils):

    @staticmethod
    def generate_notify_label(mentor_id, child_id, phone, title, deadline):
        """
        Generate a deterministic label based on task content to prevent duplicate notifications.
        """
        key = f"{mentor_id}-{child_id}-{phone}-{title}-{deadline}"
        return "task_notify_" + hashlib.md5(key.encode()).hexdigest()


    @staticmethod
    def assign_task_to_child(mentor: Mentor, task: Task, child: Child):
        """Assign a task to a child and link the mentor to the task."""
        if child not in mentor.children.all():
            raise ValueError("Mentor does not have permission to assign tasks to this child.")
        
        # Create a task assignment entry
        assignment = TaskAssignment.objects.create(
            task=task,
            child=child,
            assigned_by=mentor.user  
        )
        return assignment

    @staticmethod
    def approve_task_completion_by_mentor(mentor: Mentor, task_completion: TaskCompletion):
        """Approve a task if the mentor has enough TeenCoins."""
        if task_completion.status == 'approved':
            raise ValueError("Task completion is already approved.")
        
        # Check if the mentor has enough available TeenCoins
        required_coins = task_completion.task.points + task_completion.bonus_points
        
        # Approve task completion
        task_completion.status = 'approved'
        task_completion.approved_by = mentor.user  # Track which mentor approved it
        task_completion.remaining_coins = required_coins
        task_completion.save()

        # Award points to the child
        task_completion.child.add_points(required_coins)

        return task_completion

    @staticmethod
    def reject_task_completion_by_mentor(mentor: Mentor, task_completion: TaskCompletion, feedback: str = None):
        """Reject a task and provide feedback."""
        if task_completion.status == 'rejected':
            raise ValueError("Task completion is already rejected.")

        task_completion.status = 'rejected'
        task_completion.mentor_feedback = feedback
        task_completion.save()
        
        return task_completion
    
    
    @staticmethod
    def get_all_tasks_assigned_to_mentor(mentor: Mentor, start_date=None, end_date=None):
        """Retrieve all tasks assigned to a specific mentor."""
        tasks = Task.objects.filter(assigned_mentors=mentor)
        if start_date and end_date:
            tasks = tasks.filter(deadline__range=(start_date, end_date))
        return tasks

    @staticmethod
    def get_mentor_children_with_completed_tasks(mentor: Mentor):
        """
        Retrieve all children assigned to the mentor and fetch their completed tasks 
        (approved tasks assigned by this mentor).
        """
        children = mentor.children.all()  # Get all children linked to this mentor

        # Create a dictionary to store child details along with their approved tasks
        mentor_children_details = {}

        for child in children:
            # Fetch only the approved task completions that were assigned by this mentor
            approved_tasks = TaskCompletion.objects.filter(
                child=child,
                status='approved',
                task__assigned_mentors=mentor  # Ensure the mentor assigned the task
            ).select_related('task')

            # Add the child and their completed tasks to the dictionary
            mentor_children_details[child] = list(approved_tasks)

        return mentor_children_details

    @staticmethod
    def assign_bonus_to_task_completion(mentor: Mentor, task_completion_id: int, bonus_points: int):
        """
        Add bonus points to a TaskCompletion, ensuring the mentor has enough TeenCoins.
        Updates the remaining coins accordingly.

        Args:
            mentor (Mentor): The mentor awarding the bonus.
            task_completion_id (int): The TaskCompletion ID to update.
            bonus_points (int): The amount of bonus points to add.

        Raises:
            ValueError: If the mentor does not have enough available TeenCoins.
        """
        # Fetch TaskCompletion instance
        task_completion = TaskCompletion.objects.filter(id=task_completion_id).first()
        if not task_completion:
            raise ValueError("TaskCompletion not found.")

        # Ensure the mentor assigned the task
        if task_completion.task not in Task.objects.filter(assigned_mentors=mentor):
            raise ValueError("Mentor does not have permission to assign a bonus for this task.")

        # Check if the mentor has enough available TeenCoins
        if mentor.available_teencoins < bonus_points:
            raise ValueError("Not enough TeenCoins to assign this bonus.")

        # Deduct the bonus from the mentor's available TeenCoins
        mentor.available_teencoins -= bonus_points
        mentor.save()

        # Add the bonus to the TaskCompletion and update remaining coins
        task_completion.bonus_points += bonus_points
        task_completion.remaining_coins += bonus_points
        task_completion.save()

        # Award points to the child
        task_completion.child.add_points(bonus_points)

        return task_completion
    
    
    @staticmethod
    def get_approved_task_completions_for_mentor_and_child(mentor: Mentor, child: Child):
        """
        Retrieve all TaskCompletion objects for a given child that are approved
        and were assigned by the given mentor.
        """
        return TaskCompletion.objects.filter(
            child=child,
            status='approved',
            task__assigned_mentors=mentor  # Ensure the task was assigned by this mentor
        ).select_related('task')

    @staticmethod
    def count_approved_task_completions_for_child_from_mentor(mentor: Mentor, child: Child):
        """
        Count the number of approved TaskCompletion objects for a given child
        that were assigned by the given mentor.
        """
        return TaskCompletion.objects.filter(
            child=child,
            status='approved',
            task__assigned_mentors=mentor  # Ensure the task was assigned by this mentor
        ).count()
        
    @staticmethod
    def get_active_tasks_for_child_from_mentor(mentor: Mentor, child: Child):
        """
        Returns active tasks assigned to a child by a specific mentor.
        """
        completed_task_ids = TaskCompletion.objects.filter(
            child=child, status="approved",
            task__assigned_mentors=mentor
        ).values_list("task_id", flat=True)

        return Task.objects.filter(
            assignments__child=child,
            assigned_mentors=mentor,
            deadline__gte=timezone.now().date()
        ).exclude(id__in=completed_task_ids).distinct()
        
    @staticmethod
    def count_total_assigned_tasks_for_child_from_mentor(mentor: Mentor, child: Child):   
        """
        Count the total number of tasks assigned to a given child by a given mentor.
        """
        return TaskAssignment.objects.filter(
            child=child,
            task__assigned_mentors=mentor,
        ).count()
    
    @staticmethod
    def get_mentor_active_tasks(mentor: Mentor, start_date=None, end_date=None):
        """
        Retrieve all tasks assigned to the given mentor, with an optional date range filter.

        Args:
            mentor (Mentor): The mentor whose tasks should be fetched.
            start_date (date, optional): Start date for filtering (inclusive).
            end_date (date, optional): End date for filtering (inclusive).

        Returns:
            QuerySet: Filtered tasks assigned to the mentor.
        """
        current_date = timezone.now().date()
        tasks = Task.objects.filter(assigned_mentors=mentor, deadline__gte=current_date)

        # Apply date range filter if provided
        if start_date and end_date:
            tasks = tasks.filter(deadline__range=(start_date, end_date))

        return tasks


    @staticmethod
    def create_task_with_assignments_async(mentor_id, children_ids, task_data):
        from mentorApp.models import Mentor
        mentor = Mentor.objects.get(id=mentor_id)
        return MentorTaskUtils.create_task_with_assignments(mentor, children_ids, task_data)  

    @staticmethod
    def create_task_with_assignments(mentor, children_ids, task_data):
        task_data.setdefault("description", "")
        task_data.pop("assigned_children", None)

        assigned_children = Child.objects.filter(id__in=children_ids)
        total_cost = task_data.get("points", 0) * assigned_children.count()

        with transaction.atomic():
            mentor = Mentor.objects.select_for_update().get(id=mentor.id)

            if mentor.available_teencoins < total_cost:
                raise ValueError("Not enough TeenCoins to assign the task.")

            new_task = Task.objects.create(**task_data)
            new_task.assigned_mentors.add(mentor)
            new_task.assigned_children.set(assigned_children)

            TaskAssignment.objects.bulk_create(
                TaskAssignment(task=new_task, child=ch, assigned_by=mentor.user)
                for ch in assigned_children
            )

            mentor.available_teencoins -= total_cost
            mentor.save()

        if new_task.send_whatsapp_on_assign:
            for child in assigned_children.select_related("user__personal_info", "subscription"):
                phone = getattr(child.user.personal_info, "phone_number", None)
                subscription = getattr(child, "subscription", None)
                if not phone or not subscription or not subscription.is_active():
                    continue
                try:
                    NotificationManager.sent_whatsapp(
                        f"היי {child.user.username} 😎\n"
                        f"קיבלת משימה חדשה! 📣\n\n"
                        f"📝 משימה: *{new_task.title}*\n"
                        f"📅 מועד סיום: {new_task.deadline:%d/%m/%Y}\n"
                        f"⭐ ניקוד: {new_task.points} Teencoins\n\n"
                        f"📲 כנס לראות את כל הפרטים: https://www.volunteen.site/child/home/\n"
                        f"בהצלחה! – צוות Volunteen🧡",
                        phone,
                    )
                except Exception as exc:
                    print(f"Failed to send WhatsApp message: {exc}")

        return new_task
    
    
    @staticmethod
    def get_template_tasks(mentor, search_query=''):
        """
        Returns a queryset of tasks that are marked as templates
        and are assigned to the given mentor. Optionally filters by search_query.
        """
        queryset = Task.objects.filter(is_template=True, assigned_mentors=mentor)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            )
        return queryset
    
    @staticmethod
    def get_active_completions_for_mentor_child(mentor, child):
        """
        Returns a list of approved TaskCompletion objects for this child
        that were assigned by the given mentor and have NOT yet expired.
        """
        now = timezone.now()
        completions = TaskCompletion.objects.filter(
            child=child,
            task__assigned_mentors=mentor,
            status='approved'
        )
        active_completions = []
        for tc in completions:
            expiry_date = tc.completion_date + relativedelta(months=TEEN_COINS_EXPIRATION_MONTHS)
            if expiry_date > now:
                active_completions.append(tc)
        return active_completions
    
    @staticmethod
    def get_children_with_completed_tasks_for_mentor(mentor):
        """
        Retrieves children assigned to the mentor, prefetching approved task completions 
        for tasks assigned by the mentor and aggregates total points (task points + bonus points).
        """
        # Prefetch only task completions for tasks assigned by this mentor
        children = mentor.children.prefetch_related(
            Prefetch(
                'taskcompletion_set',
                queryset=TaskCompletion.objects.filter(
                    status='approved',
                    task__assigned_mentors=mentor
                ).select_related('task').order_by('-completion_date')
            )
        ).order_by('-points')

        # Aggregate points for each child based on tasks assigned by this mentor
        for child in children:
            total = TaskCompletion.objects.filter(
                child=child,
                task__assigned_mentors=mentor,
                status='approved',
            ).aggregate(
                total_points=Sum(F('task__points') + F('bonus_points'), output_field=IntegerField())
            )
            child.task_total_points = total['total_points'] or 0
        return children
    
    
    @staticmethod
    def get_approved_completions_for_task(mentor: Mentor, task: Task):
        """
        Retrieve all approved TaskCompletion objects for a given task.

        This method first checks that the task is assigned to the mentor.
        Then it returns all TaskCompletion instances for the task with status 'approved'.
        """
        # Ensure the task is assigned to the given mentor
        if not task.assigned_mentors.filter(id=mentor.id).exists():
            return TaskCompletion.objects.none()
        
        return TaskCompletion.objects.filter(task=task, status='approved')
