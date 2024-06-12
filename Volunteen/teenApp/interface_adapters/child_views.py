from django.shortcuts import render
from datetime import datetime
from django.db.models import Sum, F
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from teenApp.entities.child import Child
from teenApp.entities.task import Task
from teenApp.entities.redemption import Redemption
from teenApp.entities.shop import Shop
from datetime import date
from django.utils.timezone import now
from django.db.models import Sum, F
from django.templatetags.static import static
from teenApp.interface_adapters.forms import DateRangeForm
@login_required
def child_home(request):
    child = Child.objects.get(user=request.user)
    greetings = {
        0: f"שיהיה לך פתיחה חזקה לשבוע! תתחיל לאסוף נקודות ולהגשים את החלומות שלך!",  # יום ראשון
        1: f"זה יום שני! תמשיך לשאוף למעלה ולכוון גבוה! אתה בדרך להצלחה!",
        2: f"זה יום שלישי! הזמן להראות את הכוח והנחישות שלך! אתה יכול לעשות הכל!",
        3: f"זה יום רביעי! אתה כבר באמצע השבוע, תמשיך להתקדם ולכבוש מטרות!",
        4: f"זה יום חמישי! כמעט סיימת את השבוע, תשמור על קצב חזק ותגיע למטרה!",
        5: f"שישי שמח! תחגוג את ההישגים שלך ותהנה מהיום! אתה בדרך הנכונה!",  # יום שישי
        6: f"זה יום שבת! תמשיך לפעול ולהתקדם לקראת שבוע חדש ומוצלח!",
    }

    today = datetime.today().weekday()+1
    greeting = greetings.get(today, f"Hey {child.user.username}, have a great day!")
    
    new_tasks = child.assigned_tasks.filter(new_task=True, viewed=False)
    new_tasks_count = new_tasks.count()

    if request.method == 'POST' and 'close_notification' in request.POST:
        new_tasks.update(viewed=True)
        new_tasks.update(new_task=False)

    return render(request, 'child_home.html', {'child': child, 'greeting': greeting, 'new_tasks_count': new_tasks_count, 'new_tasks': new_tasks})

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

    tasks = child.tasks_completed.all()
    if start_date and end_date:
        tasks = tasks.filter(completed_date__range=(start_date, end_date))

    for task in tasks:
        completion_date = task.completed_date.date() if task.completed_date else default_date
        tasks_with_bonus.append({
            'title': task.title,
            'points': task.points,
            'completion_date': completion_date,
            'mentor': ", ".join(mentor.user.username for mentor in task.assigned_mentors.all())
        })
        if task.total_bonus_points > 0:
            tasks_with_bonus.append({
                'title': f"{task.title} - Bonus",
                'points': task.total_bonus_points,
                'completion_date': completion_date,
                'mentor': ", ".join(mentor.user.username for mentor in task.assigned_mentors.all())
            })

    return render(request, 'child_completed_tasks.html', {'tasks_with_bonus': tasks_with_bonus, 'form': form})

@login_required
def child_active_list(request):
    try:
        child = Child.objects.get(user=request.user)
        tasks = Task.objects.filter(assigned_children=child, completed=False).order_by('deadline') 
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

    tasks = child.tasks_completed.all()
    if start_date and end_date:
        tasks = tasks.filter(completed_date__range=(start_date, end_date))

    for task in tasks:
        completed_date = task.completed_date.date() if task.completed_date else default_date
        current_points += task.points
        string=f" ביצוע משימה : {task.title }"
        points_history.append({
            'description': f"Completed Task: {task.title}",
            'points': f"+{task.points}",
            'date': completed_date,
            'balance': current_points,
            'string':string
        })
        if task.total_bonus_points > 0:
            current_points += task.total_bonus_points
            string=f"{task.title } :בונוס"
            points_history.append({
                'description': f"Bonus Points for Task: {task.title}",
                'points': f"+{task.total_bonus_points}",
                'date': completed_date,
                'balance': current_points,
                'string':string
            })

    redemptions = Redemption.objects.filter(child=child)
    if start_date and end_date:
        redemptions = redemptions.filter(date_redeemed__range=(start_date, end_date))

    for redemption in redemptions:
        date_redeemed = redemption.date_redeemed if redemption.date_redeemed else default_date
        current_points -= redemption.points_used
        string=f" רכישה :{redemption.shop.name}"
        points_history.append({
            'description': f"Redeemed: {redemption.shop.name}",
            'points': f"-{redemption.points_used}",
            'date': date_redeemed.date(),
            'balance': current_points,
            'string':string
        })
    points_history.sort(key=lambda x: x['date'])  # סידור לפי תאריך
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

def update_monthly_top_children():
    current_date = now()
    first_day_of_current_month = current_date.replace(day=1)
    first_day_of_next_month = (first_day_of_current_month + timedelta(days=32)).replace(day=1)
    
    children = Child.objects.all().order_by('-points')[:3]
    positions = [20, 10, 5]  # בונוסים לפי מיקום

    for i, child in enumerate(children):
        MonthlyTopChild.objects.create(
            child=child,
            points=child.points,
            month=first_day_of_current_month,
            position=i + 1
        )
        child.points += positions[i]
        child.save()

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
                    When(tasks_completed__completed_date__range=(start_date, end_date), then='tasks_completed__points'),
                    When(redemptions__date_redeemed__range=(start_date, end_date), then=-F('redemptions__points_used')),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )
        ).order_by('-points_within_range')
    else:
        children = children.order_by('-points')

    return render(request, 'points_leaderboard.html', {'children': children, 'form': form})

def points_leaderboard(request):
    children = Child.objects.all().order_by('-points')
    return render(request, 'points_leaderboard.html', {'children': children})