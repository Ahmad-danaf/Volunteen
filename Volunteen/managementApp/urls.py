from django.urls import path
from . import views

app_name = 'managementApp'

urlpatterns = [
    path('donation-manager-dashboard/', views.donation_manager_dashboard, name='donation_manager_dashboard'),
    path('donation-summary-by-category/', views.donation_summary_by_category, name='donation_summary_by_category'),
    
]
