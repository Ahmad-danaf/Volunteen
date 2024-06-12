from django.urls import path
from teenApp.interface_adapters import views, child_views, shop_views, mentor_views
from django.contrib.auth.models import User
from django.db import models

User.add_to_class('phone', models.CharField(unique=True, max_length=10, blank=True, null=True))

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),  # Redirects users to the appropriate home page
    path('child/', child_views.child_home, name='child_home'),  # Child home page
    path('mentor/', mentor_views.mentor_home, name='mentor_home'),  # Mentor home page
    path('list/', views.list_view, name='list'),  # List tasks from external API
    path('shop_redeem/', shop_views.shop_redeem_points, name='shop_redeem_points'),  # Handle points redemption for children
    path('default_home/', views.default_home, name='default_home'),  # Default home page
    path('shop_home/', shop_views.shop_home, name='shop_home'),  # Shop home page
    path('logout/', views.logout_view, name='logout_view'),  # Handle user logout
    path('redemption-history/', child_views.child_redemption_history, name='child_redemption_history'),
    path('completed-tasks/', child_views.child_completed_tasks, name='child_completed_tasks'),
    path('completed_tasks/', mentor_views.mentor_completed_tasks_view, name='mentor_completed_tasks'),
    path('shop_redemption_history/', shop_views.shop_redemption_history, name='shop_redemption_history'),
    path('rewards/', child_views.rewards_view, name='reward'),  # List available rewards
    path('mentor/children-details/', mentor_views.mentor_children_details, name='mentor_children_details'), 
    path('mentor/active-list/', mentor_views.mentor_active_list, name='mentor_active_list'), 
    path('child/active-list/', child_views.child_active_list, name='child_active_list'), 
    path('mentor/assign-points/', mentor_views.assign_points, name='assign_points'),  # Assign points to children
    path('mentor/assign-points/<int:task_id>/', mentor_views.assign_points, name='assign_points'),  # Assign points to children for a specific task
    path('mentor/task-list/', mentor_views.mentor_task_list, name='mentor_task_list'),
    path('mentor/assign-task/<int:task_id>/', mentor_views.assign_task, name='assign_task'),
    path('cancel_transaction/', shop_views.shop_cancel_transaction, name='shop_cancel_transaction'),
    path('child/points-history/', child_views.child_points_history, name='child_points_history'),
    path('mentor/assign-points/success/<int:task_id>/', mentor_views.points_assigned_success, name='points_assigned_success'),
    path('assign-bonus/', mentor_views.assign_bonus, name='assign_bonus'),
    path('cancel_transaction/', shop_views.shop_cancel_transaction, name='shop_cancel_transaction'),
    path('points-leaderboard/', child_views.points_leaderboard, name='points_leaderboard'),
    path('ajax/load-children/', mentor_views.load_children, name='load_children'),
    path('mentor/edit-task/<int:task_id>/', mentor_views.edit_task, name='edit_task'),
    path('identify-child/', shop_views.shop_identify_child, name='shop_identify_child'),
    path('complete-transaction/', shop_views.shop_complete_transaction, name='shop_complete_transaction'),
]
