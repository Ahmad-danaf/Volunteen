from django.urls import path
from . import views

app_name = 'parentApp'

urlpatterns = [
    path('landing/', views.parent_landing, name='parent_landing'),
    path('choose-child/', views.child_selection, name='parent_home'),
    path('dashboard/<int:child_id>/', views.parent_dashboard, name='parent_dashboard'),
    path('child/tasks/<int:child_id>/', views.task_dashboard, name='task_dashboard'),
    path('child/redeemtion/<int:child_id>/', views.redeemtion_dashboard, name='redeemtion_dashboard'),
    path('child/all-rewards/<int:child_id>/', views.all_rewards, name='all_rewards'),
    path('all-children-leaderboard/', views.all_children_points_leaderboard, name='all_children_leaderboard'),
    ]