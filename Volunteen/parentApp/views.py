from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Parent
from childApp.models import Child
from teenApp.entities.task import Task
from django.shortcuts import get_object_or_404
from django.utils import timezone
from childApp.utils.child_task_manager import ChildTaskManager
from childApp.utils.ChildRedemptionManager import ChildRedemptionManager
from childApp.utils.TeenCoinManager import TeenCoinManager
from django.db.models import Prefetch, Sum
from django.utils.timezone import now
from django.templatetags.static import static
from shopApp.models import Shop, Reward, Redemption, Category
from Volunteen.constants import AVAILABLE_CITIES
from childApp.utils.leaderboard_manager import LeaderboardUtils
from teenApp.interface_adapters.forms import DateRangeCityForm

def parent_landing(request):
    return render(request, 'parent_landing.html')

def child_selection(request):
    """
    Render a page showing cards for each child.
    Each card displays a few summary details so the parent can choose a child.
    """
    # Assuming the parent's children are available as a related manager
    parent = Parent.objects.get(user=request.user)
    
    # Fetch all children linked to the parent
    children_obj = Child.objects.filter(parent=parent)
    children = list(children_obj)
    # Annotate each child with some summary details
    for child in children:
        child.assigned_tasks_count = ChildTaskManager.get_assigned_tasks_count(child)
        child.completed_tasks_count = ChildTaskManager.get_completed_tasks_count(child)
        child.teen_coins_used = ChildRedemptionManager.get_teen_coins_used(child)
        

    context = {
        'user_children': children,
    }
    return render(request, 'child_selection.html', context)


@login_required
def parent_dashboard(request,child_id):
    # Fetch the parent object
    parent = Parent.objects.get(user=request.user)
    
    selected_child  = get_object_or_404(Child, id=child_id)
    
    # Fetch summary data using your utility classes
    assigned_tasks_count = ChildTaskManager.get_assigned_tasks_count(selected_child)
    completed_tasks_count = ChildTaskManager.get_completed_tasks_count(selected_child)
    teen_coins_used = ChildRedemptionManager.get_teen_coins_used(selected_child)

    context = {
        'selected_child': selected_child,
        'selected_child_id': selected_child.id,
        'assigned_tasks_count': assigned_tasks_count,
        'completed_tasks_count': completed_tasks_count,
        'teen_coins_used': teen_coins_used,
    }
    return render(request, 'parent_dashboard.html', context)


@login_required
def task_dashboard(request, child_id):
    # Fetch the child object
    child = get_object_or_404(Child, id=child_id)

    # Get filters from request
    status_filter = request.GET.get('status', 'all')  # 'all', 'completed', 'pending'
    date_filter = request.GET.get('date', 'all')  # 'all', 'today', 'this_week', 'this_month'

    # Retrieve filtered tasks using the utility class
    filtered_tasks = ChildTaskManager.get_filtered_tasks_by_status_date(child, status_filter, date_filter)
    context = {
        'child': child,
        'all_tasks': filtered_tasks,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'task_dashboard.html', context)


@login_required
def redeemtion_dashboard(request, child_id):
    """
    Renders the Parent Redemption Rewards dashboard for the selected child.
    
    This view ensures that the child belongs to the logged-in parent
    and passes both the child's details and the available rewards to the template.
    """
    child = get_object_or_404(Child, id=child_id)
    redemptions = ChildRedemptionManager.get_all_redemptions(child)
    curr_child_points = TeenCoinManager.get_total_active_teencoins(child)
    context = {
        'child': child,
        'redemptions': redemptions,
        'curr_child_points': curr_child_points,
    }
    return render(request, 'child_redeemtion_dashboard.html', context)


@login_required
def all_rewards(request, child_id):
    # Prefetch related rewards for efficiency
    shops = Shop.objects.prefetch_related(
        Prefetch('rewards', queryset=Reward.objects.filter(is_visible=True))
    ).all()

    child = get_object_or_404(Child, id=child_id)
    child_city = child.city if child.city else ''

    # Get available categories
    available_categories = Category.objects.all().values("code", "name")

    shops_with_images = []
    for shop in shops:
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        shop_image = shop.img.url if shop.img else static('images/logo.png')
        points_left_to_spend = shop.max_points - points_used_this_month
        rewards_with_images = [
            {
                'title': reward.title,
                'img_url': reward.img.url if reward.img else static('images/logo.png'),
                'points': reward.points_required,
                'sufficient_points': child.points >= reward.points_required
            }
            for reward in shop.rewards.filter(is_visible=True)
        ]
        
        shops_with_images.append({
            'name': shop.name,
            'img': shop_image,
            'city': shop.city,  
            'rewards': rewards_with_images,
            'used_points': points_used_this_month,
            'is_open': shop.is_open(),
            'points_left_to_spend': points_left_to_spend,
            'categories': [cat.code for cat in shop.categories.all()]  # Add categories
        })
    categories_list = []
    for cat in available_categories:
        code, name = cat['code'], cat['name']
        categories_list.append({'code': code, 'name': name})
                            
    context = {
        'shops': shops_with_images,
        'child_points': child.points,
        'child_city': child_city,
        'available_cities': AVAILABLE_CITIES,
        'categories_list': categories_list, 
    }
    return render(request, 'parent_reward_list.html', context)


@login_required
def all_children_points_leaderboard(request):
    form = DateRangeCityForm(request.GET or None)
    if form.is_valid():
        city = form.cleaned_data.get('city')  
        if form.cleaned_data['start_date'] and form.cleaned_data['end_date']:
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            start_date, end_date = LeaderboardUtils.convert_dates_to_datetime_range(start_date, end_date)
        else:
            start_date = None
            end_date = None
    else:
        city = None
        start_date = None
        end_date = None

    children = LeaderboardUtils.get_children_leaderboard(start_date, end_date, city)
    return render(request, 'all_children_points_leaderboard.html', {'children': children, 'form': form})
