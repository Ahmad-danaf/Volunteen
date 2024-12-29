
from django.urls import path
from childApp.views import (
    ChildHomeView,
    ChildRedemptionHistoryView,
    ChildCompletedTasksView,
    ChildActiveListView,
    ChildPointsHistoryView,
    RewardsView,
    PointsLeaderboardView,
    save_phone_number
)

app_name='childApp'

urlpatterns = [
    path('home/', ChildHomeView.as_view(), name='child_home'),
    path('redemption-history/', ChildRedemptionHistoryView.as_view(), name='child_redemption_history'),
    path('completed-tasks/', ChildCompletedTasksView.as_view(), name='child_completed_tasks'),
    path('active-list/', ChildActiveListView.as_view(), name='child_active_list'),
    path('points-history/', ChildPointsHistoryView.as_view(), name='child_points_history'),
    path('rewards/', RewardsView.as_view(), name='rewards'),
    path('leaderboard/', PointsLeaderboardView.as_view(), name='points_leaderboard'),
    path('save-phone/', save_phone_number, name='save_phone_number'),
]
