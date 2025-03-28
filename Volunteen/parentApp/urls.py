from django.urls import path
from . import views

app_name = 'parentApp'

urlpatterns = [
    path('landing/', views.parent_landing, name='parent_landing'),
    path('choose-child/', views.child_selection, name='parent_home'),
    path('dashboard/<int:child_id>/', views.parent_dashboard, name='parent_dashboard'),
    path('child/tasks/<int:child_id>/', views.mentor_task_dashboard, name='mentor_task_dashboard'),
    path('child/redeemtion/<int:child_id>/', views.redeemtion_dashboard, name='redeemtion_dashboard'),
    path('child/all-rewards/<int:child_id>/', views.all_rewards, name='all_rewards'),
    path('all-children-leaderboard/', views.all_children_points_leaderboard, name='all_children_leaderboard'),
    path('tasks-page/', views.parent_tasks_view, name='parent_tasks'),
    path('tasks/create/', views.create_parent_task, name='create_parent_task'),
    path('tasks/approve/', views.approve_task_completion, name='approve_task_completion'),
    path('tasks/reject/', views.reject_task_completion, name='reject_task_completion'),
    path('tasks/edit/<int:task_id>/', views.edit_task, name='edit_task'),
    ]