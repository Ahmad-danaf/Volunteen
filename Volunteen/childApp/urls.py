from django.urls import path
from childApp import views as child_views

app_name='childApp'

urlpatterns = [
    path('inactive/<int:child_id>/', child_views.inactive_home, name='inactive_home'),
    path('home/', child_views.child_home, name='child_home'),  # Child home page
    
    path('redemption-history/', child_views.child_redemption_history, name='child_redemption_history'),
    path('rewards/', child_views.rewards_view, name='reward'),  # List available rewards
    path('shop/<int:shop_id>/details/', child_views.shop_detail, name='shop_detail'),
    path('rate/<int:redemption_id>/', child_views.rate_redemption_view, name='rate_redemption'),
    path('shop/<int:shop_id>/rewards/', child_views.shop_rewards_view, name='shop_rewards'),
    path('submit_redemption_request/', child_views.submit_redemption_request, name='submit_redemption_request'),
    path('cancel_request/', child_views.cancel_request, name='cancel_request'),
    path("pending-requests/", child_views.child_not_approved_requests, name="child_not_approved_requests"),
    
    path('active-list/', child_views.child_active_list, name='child_active_list'), 
    path('points-history/', child_views.child_points_history, name='child_points_history'),
    path('points-leaderboard/', child_views.points_leaderboard, name='points_leaderboard'),

    path('landing/', child_views.child_landing, name='child_landing'), 

    path('completed-tasks/', child_views.get_reviewed_tasks, name='get_reviewed_tasks'),
    path('tasks/check-in-out/', child_views.task_check_in_out, name='task_check_in_out'),
    path('tasks/<int:task_id>/check-in/', child_views.check_in, name='check_in'),
    path('tasks/<int:task_id>/check-out/', child_views.check_out, name='check_out'),      
    path('tasks/submit-check-in/', child_views.submit_check_in, name='submit_check_in'),
    path('tasks/submit-check-out/', child_views.submit_check_out, name='submit_check_out'),
    path('tasks/no-check-in/', child_views.no_check_in, name='no_check_in'),
    path('mark-tasks-viewed/', child_views.mark_tasks_as_viewed, name='mark_tasks_as_viewed'),
    
    path('update-streak/', child_views.update_streak, name='update_streak'),
    path('top-streaks/', child_views.top_streaks, name='top_streaks'),

    path('donation-leaderboard/', child_views.donation_leaderboard, name='donation_leaderboard'),
    path('donate-coins/', child_views.donate_coins, name='donate_coins'),  # New path for donations

    path("campaigns/", child_views.CampaignListView.as_view(), name="child-campaigns"),
    path("campaigns/<int:pk>/", child_views.CampaignDetailView.as_view(), name="child-campaign-detail"),
    path("campaigns/<int:pk>/join", child_views.join_campaign_view, name="child-campaign-join"),
    path("campaigns/<int:pk>/leave", child_views.leave_campaign_view, name="child-campaign-leave"),
]
