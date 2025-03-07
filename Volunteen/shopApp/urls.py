from django.urls import path
from shopApp import views

app_name='shopApp'

urlpatterns = [
    path('shop_home/', views.shop_home, name='shop_home'),  # Shop home page
    path('shop_redemption_history/', views.shop_redemption_history, name='shop_redemption_history'),
    path('toggle-reward-visibility/<int:reward_id>/', views.toggle_reward_visibility, name='toggle_reward_visibility'),
    path('opening-hours/', views.opening_hours_view, name='opening_hours'),
    path("pending-redemption-requests/", views.pending_redemption_requests, name="pending_redemption_requests"),
    path('batch-process-requests/', views.batch_process_requests, name='batch_process_requests'),
    path('process-request/', views.process_request, name='process_request'),
    path('approve-all-pending-requests/', views.approve_all_pending_requests, name='approve_all_pending_requests'),
    path('landing/', views.shop_landing, name='shop_landing'),
    path('shop_redemptions/', views.shop_redemptions_view, name='shop_redemptions'),

]
