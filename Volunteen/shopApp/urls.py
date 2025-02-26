from django.urls import path
from shopApp import views

app_name='shopApp'

urlpatterns = [
    path('shop_redeem/', views.shop_redeem_points, name='shop_redeem_points'),  # Handle points redemption for children
    path('shop_home/', views.shop_home, name='shop_home'),  # Shop home page
    path('shop_redemption_history/', views.shop_redemption_history, name='shop_redemption_history'),
    path('cancel_transaction/', views.shop_cancel_transaction, name='shop_cancel_transaction'),
    path('cancel_transaction/', views.shop_cancel_transaction, name='shop_cancel_transaction'),
    path('identify-child/', views.shop_identify_child, name='shop_identify_child'),
    path('complete-transaction/', views.shop_complete_transaction, name='shop_complete_transaction'),
    path('toggle-reward-visibility/<int:reward_id>/', views.toggle_reward_visibility, name='toggle_reward_visibility'),
    path('opening-hours/', views.opening_hours_view, name='opening_hours'),
    path("pending-redemption-requests/", views.pending_redemption_requests, name="pending_redemption_requests"),
    path('batch-process-requests/', views.batch_process_requests, name='batch_process_requests'),
    path('process-request/', views.process_request, name='process_request'),

    path('landing/', views.shop_landing, name='shop_landing'),

]
