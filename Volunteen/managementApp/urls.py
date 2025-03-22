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
]
