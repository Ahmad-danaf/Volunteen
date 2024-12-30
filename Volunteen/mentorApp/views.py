from teenApp.use_cases import assign_bonus_points
from mentorApp.models import Mentor
from teenApp.entities.task import Task
from mentorApp.forms import TaskForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from django.db.models import Q, Sum, F, IntegerField, Prefetch
from django.utils.timezone import now
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.task import Task
from teenApp.use_cases.assign_bonus_points import AssignBonusPoints
from teenApp.interface_adapters.forms import DateRangeForm
from teenApp.interface_adapters.repositories import ChildRepository, TaskRepository, MentorRepository
from teenApp.utils import NotificationManager
from mentorApp.models import Mentor
from mentorApp.forms import BonusPointsForm, TaskForm
from childApp.models import Child
from django.shortcuts import get_object_or_404
class MentorHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        tasks = Task.objects.filter(assigned_mentors=mentor)

        # Update overdue tasks
        for task in tasks:
            if task.is_overdue():
                task.completed = True
                task.save()

        total_tasks = tasks.count()
        completed_tasks = tasks.filter(completed=True).count()
        open_tasks = total_tasks - completed_tasks
        efficiency_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0

        children_data = []
        for child in mentor.children.all():
            completed = TaskCompletion.objects.filter(child=child, task__in=tasks).count()
            assigned_tasks_by_mentor = tasks.filter(assigned_children=child).count()
            efficiency = (completed / assigned_tasks_by_mentor) * 100 if assigned_tasks_by_mentor > 0 else 0
            performance_color = "#d4edda" if efficiency >= 75 else "#f8d7da" if efficiency < 50 else "#fff3cd"
            children_data.append({
                'id': child.id,
                'name': child.user.username,
                'efficiency_rate': efficiency,
                'performance_color': performance_color,
            })

        data = {
            'mentor': {
                'id': mentor.id,
                'name': mentor.user.username,
            },
            'total_tasks': total_tasks,
            'open_tasks': open_tasks,
            'completed_tasks': completed_tasks,
            'efficiency_rate': efficiency_rate,
            'children': children_data,
            'tasks': [
                {
                    'id': task.id,
                    'name': task.title,
                    'completed': task.completed,
                    'due_date': task.deadline,
                }
                for task in tasks
            ],
        }
        return Response(data)

class MentorChildrenDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        # Prefetch task completions for each child to avoid N+1 queries
        children = mentor.children.prefetch_related(
            Prefetch(
                'taskcompletion_set',
                queryset=TaskCompletion.objects.select_related('task').order_by('-completion_date')
            )
        ).order_by('-points')

        # Prepare children data with total points calculation
        children_data = []
        for child in children:
            # Sum points from completed tasks and bonus points
            task_points = TaskCompletion.objects.filter(child=child).aggregate(
                total_task_points=Sum(F('task__points') + F('bonus_points'), output_field=IntegerField())
            )
            total_points = task_points['total_task_points'] or 0  # Fallback to 0 if no points

            children_data.append({
                'id': child.id,
                'name': child.user.username,
                'points': total_points,
                'task_completions': [
                    {
                        'task_id': tc.task.id,
                        'task_name': tc.task.title,
                        'completion_date': tc.completion_date,
                        'points': tc.task.points,
                        'bonus_points': tc.bonus_points,
                    }
                    for tc in child.taskcompletion_set.all()
                ]
            })

        return Response({'children': children_data})

class MentorCompletedTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        form = DateRangeForm(request.GET or None)
        task_data = []

        # Validate date range form
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date = None
            end_date = None

        # Fetch completed tasks assigned to the mentor
        tasks = Task.objects.filter(assigned_mentors=mentor, completed=True)
        if start_date and end_date:
            tasks = tasks.filter(deadline__range=(start_date, end_date))

        # Prepare task data
        for task in tasks:
            completions = TaskCompletion.objects.filter(task=task)
            task_info = {
                'task_id': task.id,
                'task_name': task.title,
                'deadline': task.deadline,
                'completed_by': [{'id': completion.child.id, 'name': completion.child.user.username} for completion in completions],
                'completed_count': completions.count(),
            }
            task_data.append(task_info)

        return Response({'tasks': task_data})

class AssignBonusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        form = BonusPointsForm(mentor, request.data)
        if form.is_valid():
            task = form.cleaned_data['task']
            child = form.cleaned_data['child']
            bonus_points = form.cleaned_data['bonus_points']

            # Validate bonus points limit
            if bonus_points > 10:
                return Response({'error': 'Maximum of 10 bonus points per assignment is allowed.'}, status=400)

            try:
                # Execute bonus points assignment
                assign_bonus_points.execute(task.id, child.id, mentor.id, bonus_points)
                TaskCompletion.objects.filter(task=task, child=child).update(bonus_points=bonus_points)
                return Response({'message': 'Bonus points assigned successfully.'}, status=200)
            except ValueError as e:
                return Response({'error': str(e)}, status=400)
        else:
            return Response({'error': 'Invalid form data.', 'details': form.errors}, status=400)


class EditTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """Retrieve the task details for editing."""
        try:
            task = Task.objects.get(id=task_id)
            mentor = Mentor.objects.get(user=request.user)
        except Task.DoesNotExist:
            raise NotFound("Task not found.")
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        if mentor not in task.assigned_mentors.all():
            return Response({'error': 'You do not have permission to edit this task.'}, status=403)

        form = TaskForm(instance=task, mentor=mentor)
        return Response({
            'task': {
                'id': task.id,
                'name': task.title,
                'description': task.description,
                'deadline': task.deadline,
                'assigned_children': [child.id for child in task.assigned_children.all()],
            },
            'form_fields': form.fields.keys()
        })

    def put(self, request, task_id):
        """Edit the task details."""
        try:
            task = Task.objects.get(id=task_id)
            mentor = Mentor.objects.get(user=request.user)
        except Task.DoesNotExist:
            raise NotFound("Task not found.")
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        # בדיקה אם המנטור משויך למשימה
        if mentor not in task.assigned_mentors.all():
            return Response({'error': 'You do not have permission to edit this task.'}, status=403)

        form = TaskForm(data=request.data, files=request.FILES, instance=task, mentor=mentor)
        if form.is_valid():
            form.save()
            return Response({'message': 'Task updated successfully.'}, status=200)
        else:
            return Response({'error': 'Invalid form data.', 'details': form.errors}, status=400)

class LoadChildrenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        task_id = request.query_params.get('task_id')

        if not task_id:
            raise ValidationError("Task ID is required.")

        # Filter children who completed the task
        completed_children = Child.objects.filter(
            taskcompletion__task_id=task_id  # Join with TaskCompletion model
        ).order_by('user__username')

        # Prepare response data
        children_data = [
            {'id': child.id, 'username': child.user.username}
            for child in completed_children
        ]

        return Response(children_data)


class AddTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        form = TaskForm(mentor=mentor, data=request.data)
        if form.is_valid():
            task = form.save(commit=False)
            task.mentor = mentor
            task.save()
            form.save_m2m()  # Save the many-to-many data for the form
            return Response({'message': 'Task created successfully.'}, status=201)
        else:
            return Response({'error': 'Invalid form data.', 'details': form.errors}, status=400)


class MentorActiveListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the list of active tasks assigned to the mentor."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        tasks = Task.objects.filter(assigned_mentors=mentor)
        task_list = [
            {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'deadline': task.deadline,
                'completed': task.completed,
            }
            for task in tasks
        ]

        return Response({'tasks': task_list})

class MentorTaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the list of tasks assigned to the mentor."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        current_date = now().date()
        tasks = Task.objects.filter(assigned_mentors=mentor, deadline__gte=current_date)

        # Handle date range filtering
        form = DateRangeForm(request.GET or None)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            tasks = tasks.filter(deadline__range=(start_date, end_date))

        task_list = [
            {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'deadline': task.deadline,
                'completed': task.completed,
            }
            for task in tasks
        ]

        return Response({'tasks': task_list})


class AssignTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        """Assign a task to selected children."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        task = get_object_or_404(Task, id=task_id)

        # Ensure the task belongs to the mentor
        if mentor not in task.assigned_mentors.all():
            return Response({'error': 'You do not have permission to assign this task.'}, status=403)

        selected_children_ids = request.data.get('children', [])
        if not selected_children_ids:
            raise ValidationError("No children selected for assignment.")

        # Exclude already assigned children
        children = mentor.children.exclude(id__in=task.assigned_children.values_list('id', flat=True))

        # Assign task to children
        for child_id in selected_children_ids:
            child = get_object_or_404(Child, id=child_id)
            if child not in children:
                continue
            task.assigned_children.add(child)
            task.new_task = True
            task.save()

            # Send notifications
            if child.user.email:
                NotificationManager.sent_mail(
                    f'Dear {child.user.first_name}, a new task "{task.title}" has been assigned to you. Please check and complete it by {task.deadline}.',
                    child.user.email
                )
            if child.user.phone:
                msg = (
                    f"🎉💥 טינג טינג! {child.user.username}, קיבלת משימה לוהטת שמחכה רק לך!! 💥🎉\n"
                    f"זה הזמן להרוויח {task.points} TeenCoins!!! 🔥 ולהתקדם לעבר היעד שלך!\n"
                    "כנס עכשיו ותגלה מה המשימה הסודית שלך >> https://www.volunteen.site/"
                )
                NotificationManager.sent_whatsapp(msg, str(child.user.phone))

        task.assigned_mentors.add(mentor)
        return Response({'message': f"Task '{task.title}' successfully assigned to selected children."}, status=200)

    def get(self, request, task_id):
        """Retrieve the list of children available for assignment."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        task = get_object_or_404(Task, id=task_id)
        children = mentor.children.exclude(id__in=task.assigned_children.values_list('id', flat=True))

        children_data = [{'id': child.id, 'name': child.user.username} for child in children]
        return Response({'task': {'id': task.id, 'title': task.title}, 'children': children_data})



class AssignPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """Retrieve children assigned to a task with their completion status."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        task = get_object_or_404(Task, id=task_id)

        # Get all assigned children
        assigned_children_ids = task.assigned_children.values_list('id', flat=True)
        children = mentor.children.filter(id__in=assigned_children_ids)

        # Prepare data for children with completion status
        children_with_status = [
            {
                'id': child.id,
                'name': child.user.username,
                'completed': TaskCompletion.objects.filter(task=task, child=child).exists()
            }
            for child in children
        ]

        return Response({
            'task': {'id': task.id, 'title': task.title},
            'children': children_with_status
        })

    def post(self, request, task_id):
        """Assign points to children for completing a task."""
        try:
            mentor = Mentor.objects.get(user=request.user)
        except Mentor.DoesNotExist:
            raise NotFound("Mentor not found.")

        task = get_object_or_404(Task, id=task_id)

        # Get selected children IDs
        selected_children_ids = request.data.get('children', [])
        if not selected_children_ids:
            raise ValidationError("No children selected for point assignment.")

        # Ensure children are valid and belong to the mentor
        assigned_children_ids = task.assigned_children.values_list('id', flat=True)
        valid_children = mentor.children.filter(id__in=assigned_children_ids).filter(id__in=selected_children_ids)

        # Mark task as completed for valid children
        for child in valid_children:
            task.mark_completed(child)

        return Response({'message': f"Points successfully assigned for task '{task.title}' to selected children."}, status=200)

class PointsAssignedSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        """Retrieve details of a task and the children who completed it."""
        task = get_object_or_404(Task, id=task_id)

        # Get children who completed the task
        completed_children = Child.objects.filter(
            id__in=TaskCompletion.objects.filter(task=task).values_list('child_id', flat=True)
        )

        # Prepare response data
        children_data = [
            {'id': child.id, 'name': child.user.username}
            for child in completed_children
        ]

        return Response({
            'task': {
                'id': task.id,
                'title': task.title,
                'deadline': task.deadline,
                'points': task.points,
            },
            'completed_children': children_data
        })


class SendWhatsAppMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the list of all children."""
        children = Child.objects.all()
        children_data = [{'id': child.id, 'name': child.user.username, 'phone': child.user.phone} for child in children]
        return Response({'children': children_data})

    def post(self, request):
        """Send WhatsApp messages to selected children."""
        selected_children_ids = request.data.get('children', [])
        message_text = request.data.get('message_text')

        if not selected_children_ids:
            raise ValidationError("No children selected.")
        if not message_text:
            raise ValidationError("Message text cannot be empty.")

        for child_id in selected_children_ids:
            try:
                child = Child.objects.get(id=child_id)
            except Child.DoesNotExist:
                continue  # Skip invalid child IDs

            if child.user.phone:
                NotificationManager.sent_whatsapp(
                    message_text,
                    str(child.user.phone)
                )

        return Response({'message': 'WhatsApp messages sent successfully.'}, status=200)
