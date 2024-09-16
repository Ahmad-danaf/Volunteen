from django.shortcuts import render
from datetime import datetime
from django.db.models import Sum, F
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from teenApp.entities.child import Child
from teenApp.entities.task import Task
from teenApp.entities.redemption import Redemption
from teenApp.entities.shop import Shop
from teenApp.entities.TaskCompletion import TaskCompletion
from datetime import date
from django.utils.timezone import now
from django.utils import timezone
from django.db.models import Sum, F
from django.templatetags.static import static
from teenApp.interface_adapters.forms import DateRangeForm
from django.db.models import Sum, Case, When, Value, IntegerField, F

@login_required
def child_home(request):
    child = Child.objects.get(user=request.user)
   # Get the current day of the week (0 for Sunday, 6 for Saturday)
    current_day = datetime.now().weekday()

    # Adjusting for 0-Sunday format, since Python's weekday() starts at 0-Monday
    # We'll shift by 1 so that 0 becomes Sunday, 1 becomes Monday, etc.
    current_day = (current_day + 1) % 7

    # Greetings dictionary
    greetings = {
        0: f"שיהיה לך פתיחה חזקה לשבוע! תתחיל לאסוף נקודות ולהגשים את החלומות שלך!",  # יום ראשון
        1: f"זה יום שני! תמשיך לשאוף למעלה ולכוון גבוה! אתה בדרך להצלחה!",
        2: f"זה יום שלישי! הזמן להראות את הכוח והנחישות שלך! אתה יכול לעשות הכל!",
        3: f"זה יום רביעי! אתה כבר באמצע השבוע, תמשיך להתקדם ולכבוש מטרות!",
        4: f"זה יום חמישי! כמעט סיימת את השבוע, תשמור על קצב חזק ותגיע למטרה!",
        5: f"שישי שמח! תחגוג את ההישגים שלך ותהנה מהיום! אתה בדרך הנכונה!",  # יום שישי
        6: f"זה יום שבת! תמשיך לפעול ולהתקדם לקראת שבוע חדש ומוצלח!",
    }

    # Get the greeting for today
    todays_greeting = greetings[current_day]
    

    
    new_tasks = child.assigned_tasks.filter(new_task=True, viewed=False)
    new_tasks_count = new_tasks.count()

    if request.method == 'POST' and 'close_notification' in request.POST:
        new_tasks.update(viewed=True)
        new_tasks.update(new_task=False)

    return render(request, 'child_home.html', {'child': child, 'greeting': todays_greeting, 'new_tasks_count': new_tasks_count, 'new_tasks': new_tasks})

@login_required
def child_redemption_history(request):
    child = Child.objects.get(user=request.user)
    form = DateRangeForm(request.GET or None)
    redemptions = Redemption.objects.filter(child=child).order_by('-date_redeemed')
    default_date = date(2201, 1, 1)  

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = None
        end_date = None

    if start_date and end_date:
        redemptions = redemptions.filter(date_redeemed__range=(start_date, end_date))

    return render(request, 'child_redemption_history.html', {'redemptions': redemptions, 'form': form})

@login_required
def child_completed_tasks(request):
    child = Child.objects.get(user=request.user)
    form = DateRangeForm(request.GET or None)
    tasks_with_bonus = []
    default_date = date(2201, 1, 1)

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = None
        end_date = None

    # Retrieve TaskCompletion records associated with this child
    task_completions = TaskCompletion.objects.filter(child=child)

    if start_date and end_date:
        task_completions = task_completions.filter(completion_date__range=(start_date, end_date))

    for task_completion in task_completions:
        completion_date = task_completion.completion_date if task_completion.completion_date else default_date
        task = task_completion.task
        tasks_with_bonus.append({
            'title': task.title,
            'points': task_completion.task.points,
            'completion_date': completion_date,
            'mentor': ", ".join(mentor.user.username for mentor in task.assigned_mentors.all())
        })
       

    return render(request, 'child_completed_tasks.html', {'tasks_with_bonus': tasks_with_bonus, 'form': form})

@login_required
def child_active_list(request):
    try:
        child = Child.objects.get(user=request.user)
        tasks = Task.objects.filter(
            assigned_children=child,
            completed=False,
            deadline__gte=timezone.now().date()  
        ).order_by('deadline')
        tasks.update(new_task=False)
        return render(request, 'list_tasks.html', {'tasks': tasks})
    except Child.DoesNotExist:
        return render(request, 'list_tasks.html', {'error': 'You are not authorized to view this page.'})

@login_required
def child_points_history(request):
    child = Child.objects.get(user=request.user)
    form = DateRangeForm(request.GET or None)
    points_history = []
    current_points = 0
    default_date = date(2201, 1, 1)

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    else:
        start_date = None
        end_date = None

    # Retrieve TaskCompletion records for this child
    task_completions = TaskCompletion.objects.filter(child=child)
    if start_date and end_date:
        task_completions = task_completions.filter(completion_date__range=(start_date, end_date))

    for task_completion in task_completions:
        completed_date = task_completion.completion_date.date() if task_completion.completion_date else default_date
        task = task_completion.task
        current_points += task_completion.task.points
        string = f" ביצוע משימה : {task.title}"
        points_history.append({
            'description': f"Completed Task: {task.title}",
            'points': f"+{task.points}",
            'date': completed_date,
            'balance': current_points,
            'string': string
        })
        if task_completion.bonus_points > 0:
            current_points += task_completion.bonus_points
            string=f"{task.title } :בונוס"
            points_history.append({
                'description': f"Bonus Points for Task: {task.title}",
                'points': f"+{task_completion.bonus_points}",
                'date': completed_date,
                'balance': current_points,
                'string':string
            })


        

    
    # Retrieve redemptions for this child
    redemptions = Redemption.objects.filter(child=child)
    if start_date and end_date:
        redemptions = redemptions.filter(date_redeemed__range=(start_date, end_date))

    for redemption in redemptions:
        date_redeemed = redemption.date_redeemed if redemption.date_redeemed else default_date
        current_points -= redemption.points_used
        string = f" רכישה :{redemption.shop.name}"
        points_history.append({
            'description': f"Redeemed: {redemption.shop.name}",
            'points': f"-{redemption.points_used}",
            'date': date_redeemed.date(),
            'balance': current_points,
            'string': string
        })

    # Sort the points history by date
    points_history.sort(key=lambda x: x['date'])
    
    return render(request, 'child_points_history.html', {'points_history': points_history, 'form': form})


def rewards_view(request):
    # Prefetch related rewards to minimize database hits
    shops = Shop.objects.prefetch_related('rewards').all()

    # Get current child from request user
    child = request.user.child

    # Prepare a new list to hold shops with modified data
    shops_with_images = []
    for shop in shops:
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        # Assign default image if none exists
        shop_image = shop.img.url if shop.img else static('images/logo.png')
        
        # Prepare rewards, assigning default images if necessary
        rewards_with_images = [
            {
                'title': reward.title,
                'img_url': reward.img.url if reward.img else static('images/logo.png'),
                'points': reward.points_required,
                'sufficient_points': child.points >= reward.points_required
            }
            for reward in shop.rewards.all()
        ]
        
        # Append modified shop data to the list
        shops_with_images.append({
            'name': shop.name,
            'img': shop_image,
            'rewards': rewards_with_images,
            'used_points': points_used_this_month
        })

    context = {'shops': shops_with_images, 'child_points': child.points}
    return render(request, 'reward.html', context)

@login_required
def points_leaderboard(request):
    form = DateRangeForm(request.GET or None)
    children = Child.objects.all()

    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        
        # Calculate points within the date range
        children = children.annotate(
            points_within_range=Sum(
                Case(
                    When(completed_tasks__completed_date__range=(start_date, end_date), then='completed_tasks__points'),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).annotate(
            total_points=F('points_within_range') + F('points')
        ).order_by('-total_points')
    else:
        children = children.order_by('-points')

    return render(request, 'points_leaderboard.html', {'children': children, 'form': form})
