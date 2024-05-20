from django.urls import path
from . import views
urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),  # Redirects users to the appropriate home page
    path('child/', views.child_home, name='child_home'),  # Child home page
    path('mentor/', views.mentor_home, name='mentor_home'),  # Mentor home page
    path('mentor/points-summary/', views.mentor_points_summary, name='mentor_points_summary'),  # Mentor points summary
    path('list/', views.list_view, name='list'),  # List tasks from external API
    path('shop_redeem/', views.redeem_points, name='redeem_points'),  # Handle points redemption for children
    path('default_home/', views.default_home, name='default_home'),  # Default home page
    path('shop_home/', views.shop_home, name='shop_home'),  # Shop home page
    path('logout/', views.logout_view, name='logout_view'),  # Handle user logout
    path('redemption-history/', views.redemption_history, name='redemption_history'),
    path('completed-tasks/', views.completed_tasks, name='completed_tasks'),
    path('completed_tasks/', views.mentor_completed_tasks_view, name='mentor_completed_tasks'),
    path('shop_redemption_history/', views.shop_redemption_history, name='shop_redemption_history'),
    path('rewards/', views.rewards_view, name='reward'), # List available rewards

]
