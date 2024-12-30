from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from childApp.serializers import ChildSerializer
from teenApp.serializers import TaskSerializer
from childApp.models import Child
from teenApp.entities.task import Task
from shopApp.models import Redemption, Shop, Reward
from shopApp.serializers import RedemptionSerializer
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.interface_adapters.forms import DateRangeForm
from django.utils.timezone import now
from datetime import datetime, date
from django.db.models import Sum, Case, When, Value, IntegerField, F,Min, Max
import json
from django.templatetags.static import static
from rest_framework import status

class ChildHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response({"error": "Child not found"}, status=404)

        # Get the current day of the week
        current_day = (datetime.now().weekday() + 1) % 7

        greetings = {
            0: "שיהיה לך פתיחה חזקה לשבוע! תתחיל לאסוף נקודות ולהגשים את החלומות שלך!",
            1: "זה יום שני! תמשיך לשאוף למעלה ולכוון גבוה! אתה בדרך להצלחה!",
            2: "זה יום שלישי! הזמן להראות את הכוח והנחישות שלך! אתה יכול לעשות הכל!",
            3: "זה יום רביעי! אתה כבר באמצע השבוע, תמשיך להתקדם ולכבוש מטרות!",
            4: "זה יום חמישי! כמעט סיימת את השבוע, תשמור על קצב חזק ותגיע למטרה!",
            5: "שישי שמח! תחגוג את ההישגים שלך ותהנה מהיום! אתה בדרך הנכונה!",
            6: "זה יום שבת! תמשיך לפעול ולהתקדם לקראת שבוע חדש ומוצלח!",
        }

        todays_greeting = greetings[current_day]

        # Serialize the child object
        serialized_child = ChildSerializer(child).data

        # Get new tasks and serialize them
        new_tasks = child.assigned_tasks.filter(new_task=True, viewed=False)
        serialized_tasks = TaskSerializer(new_tasks, many=True).data

        return Response({
            "child": serialized_child,
            "greeting": todays_greeting,
            "new_tasks_count": len(new_tasks),
            "new_tasks": serialized_tasks,
        })


class ChildRedemptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch child object
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response({"error": "Child not found"}, status=404)

        # Handle date range form
        form = DateRangeForm(request.GET or None)
        if not form.is_valid():
            return Response({"error": "Invalid date range provided"}, status=400)

        # Filter redemptions by date range
        redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if start_date and end_date:
            redemptions = redemptions.filter(date_redeemed__range=(start_date, end_date))

        # Serialize redemptions
        redemption_data = RedemptionSerializer(redemptions, many=True).data

        return Response({"redemptions": redemption_data})

    def post(self, request):
        try:
            # Fetch child object
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response({"error": "Child not found"}, status=404)

        # Parse request data
        data = request.data
        redemption_id = data.get("redemption_id")

        if not redemption_id:
            return Response({"error": "Redemption ID is required"}, status=400)

        # Fetch redemption object and validate it
        try:
            redemption = Redemption.objects.get(id=redemption_id, child=child)
        except Redemption.DoesNotExist:
            return Response({"error": "Redemption not found or unauthorized"}, status=404)

        # Perform any action you need with the redemption
        # (e.g., update, verify, etc.)
        redemption.verified = True
        redemption.save()

        return Response({"success": True, "message": "Redemption verified successfully"})

class ChildCompletedTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch child object
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response({"error": "Child not found"}, status=status.HTTP_404_NOT_FOUND)

        # Handle date range form
        form = DateRangeForm(request.GET or None)
        if not form.is_valid():
            return Response({"error": "Invalid date range provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Filter task completions by date range
        task_completions = TaskCompletion.objects.filter(child=child)
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        if start_date and end_date:
            task_completions = task_completions.filter(completion_date__range=(start_date, end_date))

        # Prepare tasks with bonus data
        tasks_with_bonus = [
            {
                "title": task_completion.task.title,
                "points": task_completion.task.points,
                "completion_date": task_completion.completion_date or date(2201, 1, 1),
                "mentor": ", ".join(mentor.user.username for mentor in task_completion.task.assigned_mentors.all())
            }
            for task_completion in task_completions
        ]

        return Response({"tasks_with_bonus": tasks_with_bonus}, status=status.HTTP_200_OK)

class ChildActiveListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch the child object for the authenticated user
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response(
                {"error": "You are not authorized to view this page."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Filter active tasks assigned to the child
        tasks = Task.objects.filter(
            assigned_children=child,
            completed=False,
            deadline__gte=now().date()
        ).order_by('deadline')

        # Mark tasks as not new
        tasks.update(new_task=False)

        # Prepare task data for the response
        task_data = [
            {
                "title": task.title,
                "deadline": task.deadline,
            } for task in tasks
        ]

        return Response({"tasks": task_data}, status=status.HTTP_200_OK)

class ChildPointsHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            child = Child.objects.get(user=request.user)
        except Child.DoesNotExist:
            return Response(
                {"error": "Child not found for the logged-in user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Handle form for date range
        form = DateRangeForm(request.GET or None)
        points_history = []
        current_points = 0
        default_date = date(2201, 1, 1)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date, end_date = None, None

        # Task completions within date range
        task_completions = TaskCompletion.objects.filter(child=child)
        if start_date and end_date:
            task_completions = task_completions.filter(completion_date__range=(start_date, end_date))

        for task_completion in task_completions:
            completed_date = (
                task_completion.completion_date.date()
                if task_completion.completion_date else default_date
            )
            task = task_completion.task
            current_points += task.points

            # Add task completion details
            points_history.append({
                "description": f"Completed Task: {task.title}",
                "points": f"+{task.points}",
                "date": completed_date,
                "balance": current_points,
            })

            # Add bonus points if applicable
            if task_completion.bonus_points > 0:
                current_points += task_completion.bonus_points
                points_history.append({
                    "description": f"Bonus Points for Task: {task.title}",
                    "points": f"+{task_completion.bonus_points}",
                    "date": completed_date,
                    "balance": current_points,
                })

        # Redemptions within date range
        redemptions = Redemption.objects.filter(child=child)
        if start_date and end_date:
            redemptions = redemptions.filter(date_redeemed__range=(start_date, end_date))

        for redemption in redemptions:
            date_redeemed = redemption.date_redeemed if redemption.date_redeemed else default_date
            current_points -= redemption.points_used
            points_history.append({
                "description": f"Redeemed: {redemption.shop.name}",
                "points": f"-{redemption.points_used}",
                "date": date_redeemed.date(),
                "balance": current_points,
            })

        # Sort points history by date
        points_history.sort(key=lambda x: x["date"])

        return Response({"points_history": points_history}, status=status.HTTP_200_OK)

class RewardsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shops = Shop.objects.prefetch_related(
            Prefetch('rewards', queryset=Reward.objects.filter(is_visible=True))
        ).all()
        child = Child.objects.get(user=request.user)

        shops_with_images = []
        for shop in shops:
            start_of_month = now().replace(day=1)
            redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
            points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
            shop_image = shop.img.url if shop.img else static('images/logo.png')

            rewards_with_images = [
                {
                    'title': reward.title,
                    'img_url': reward.img.url if reward.img else static('images/logo.png'),
                    'points': reward.points_required,
                    'sufficient_points': child.points >= reward.points_required
                } for reward in shop.rewards.filter(is_visible=True)
            ]

            shops_with_images.append({
                'name': shop.name,
                'img': shop_image,
                'rewards': rewards_with_images,
                'used_points': points_used_this_month
            })

        return Response({"shops": shops_with_images, "child_points": child.points})

class PointsLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        form = DateRangeForm(request.GET or None)
        children = Child.objects.all()

        default_start_date = TaskCompletion.objects.aggregate(Min('completion_date'))['completion_date__min']
        default_end_date = TaskCompletion.objects.aggregate(Max('completion_date'))['completion_date__max']

        if form.is_valid() and form.cleaned_data['start_date'] and form.cleaned_data['end_date']:
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date = default_start_date
            end_date = default_end_date

        if start_date and end_date:
            children = children.annotate(
                task_points_within_range=Sum(
                    Case(
                        When(
                            taskcompletion__completion_date__range=(start_date, end_date),
                            then=F('taskcompletion__task__points') + F('taskcompletion__bonus_points')
                        ),
                        default=Value(0),
                        output_field=IntegerField()
                    )
                )
            ).order_by('-task_points_within_range')
        else:
            children = children.annotate(
                task_points_within_range=Value(0, output_field=IntegerField())
            )

        total_children = children.count()
        leaderboard = []
        for index, child in enumerate(children, start=1):
            rank_progress = 100 - ((index - 1) * (100 / total_children))
            leaderboard.append({
                "child_name": child.user.username,
                "points": child.task_points_within_range,
                "rank_progress": rank_progress
            })

        return Response({"leaderboard": leaderboard})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_phone_number(request):
    data = json.loads(request.body)
    phone_number = data.get("phone_number")

    if not phone_number:
        return Response({"success": False, "error": "Phone number is required."}, status=400)

    child = Child.objects.get(user=request.user)
    child.user.phone = phone_number
    child.user.save()

    return Response({"success": True})
