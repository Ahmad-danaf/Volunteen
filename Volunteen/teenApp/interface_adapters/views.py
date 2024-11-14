from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib import admin
from teenApp.entities.child import Child
from teenApp.entities.reward import Reward
from .forms import TaskForm 
from django.http import HttpResponse, JsonResponse
from teenApp.entities.task import Task
from teenApp.entities.mentor import Mentor
from teenApp.entities.redemption import Redemption
from teenApp.entities.shop import Shop
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from teenApp.use_cases.assign_task import AssignTaskToChildren
from teenApp.use_cases.assign_points import AssignPointsToChildren
from teenApp.use_cases.assign_bonus_points import AssignBonusPoints
from teenApp.use_cases.manage_child import ManageChild
from .forms import RedemptionForm, IdentifyChildForm, TaskImageForm, BonusPointsForm
import random
from datetime import datetime
from django.utils.timezone import now
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.templatetags.static import static
from django.http import HttpResponse
import json
from django.contrib.auth import logout
from teenApp.utils import NotificationManager
from teenApp.interface_adapters.forms import DateRangeForm,DateRangeMForm

@login_required
def logout_view(request):
    logout(request)
    return redirect('two_factor:login')
def landing_page(request):
    return render(request, 'landing_page.html')
@login_required
def home_redirect(request):
    if request.user.groups.filter(name='Children').exists():
        return redirect('child_home')
    elif request.user.groups.filter(name='Mentors').exists():
        return redirect('mentor_home')
    elif request.user.groups.filter(name='Shops').exists():
        return redirect('shop_home')
    else:
        return redirect('/admin')

def default_home(request):
    return HttpResponse("Home")


@login_required
def list_view(request):
    tasks = Task.objects.all()
    return render(request, 'list_tasks.html', {'tasks': tasks})

