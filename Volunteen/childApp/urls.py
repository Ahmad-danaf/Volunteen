from django.urls import path
from childApp import views as child_views

app_name='childApp'

urlpatterns = [
    path('home/', child_views.child_home, name='child_home'),  # Child home page
    path('redemption-history/', child_views.child_redemption_history, name='child_redemption_history'),
    path('completed-tasks/', child_views.child_completed_tasks, name='child_completed_tasks'),
    path('rewards/', child_views.rewards_view, name='reward'),  # List available rewards
    path('active-list/', child_views.child_active_list, name='child_active_list'), 
    path('points-history/', child_views.child_points_history, name='child_points_history'),
    path('points-leaderboard/', child_views.points_leaderboard, name='points_leaderboard'),
    path('save_phone_number/', child_views.save_phone_number, name='save_phone_number'),
    path('rate/<int:redemption_id>/', child_views.rate_redemption_view, name='rate_redemption'),

]
