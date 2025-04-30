from django.urls import path
from . import views

app_name = 'managementApp'

urlpatterns = [
    path('donation-manager-dashboard/', views.donation_manager_dashboard, name='donation_manager_dashboard'),
    path('donation-summary-by-category/', views.donation_summary_by_category, name='donation_summary_by_category'),
    path('add-spending/', views.add_spending, name='add_spending'),
    path('recent-donations/', views.recent_donations, name='recent_donations'),
    path('download-report/', views.download_report, name='download_report'),
    path('top-donors/', views.top_donors, name='top_donors'),
    path('recent-spendings/', views.recent_spendings, name='recent_spendings'),
    path('spending/<int:spending_id>/', views.spending_detail, name='spending_detail'),
    path('all-spendings/', views.all_spendings, name='all_spendings'),
    path('category-donors/<int:category_id>/', views.category_donors, name='category_donors'),
    path('shops/summary/', views.shop_summary, name='shop_summary'),
    path('shops/report/', views.download_shop_report, name='download_shop_report'),
    path('shop/<int:shop_id>/', views.shop_detail, name='shop_detail'),
    path("donation/simulate/", views.simulate_donation_spend_view, name="simulate_donation_spend"),

    ###############CAMPAIGN MANAGER################
    path("campaign/manager_home/", views.campaign_manager_home, name="campaign_manager_home"),
    path('campaigns/list/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/step1/', views.create_campaign_step1, name='create_campaign_step1'),
    path('campaigns/create/step2/', views.create_campaign_step2, name='create_campaign_step2'),
    path('campaigns/create/step3/', views.create_campaign_step3, name='create_campaign_step3'),
    path("campaign/approvals/", views.campaign_approvals_panel, name="campaign_approvals_panel"),
    path("campaign/<int:campaign_id>/participants/", views.track_campaign_participants, name="track_campaign_participants"),
    path("campaign/<int:campaign_id>/remove_child/<int:child_id>/", views.remove_child_from_campaign, name="remove_child_from_campaign"),
    
    
    
]
