from django.urls import path
from institutionApp import views

app_name = 'institutionApp'  
urlpatterns = [
    path('home/', views.institution_home, name='institution_home'),  # ✅ חייב להיות כאן
    path('transfer-teencoins/', views.transfer_teencoins_to_mentor, name='transfer_teencoins'),
    path('transfer-between-mentors/', views.transfer_between_mentors, name='transfer_between_mentors'),
    path('transfer-history/', views.get_transfer_history, name='transfer_history'),
    path('balances/', views.institution_balances, name='institution_balances'),
    path('mentor-management/', views.mentor_management, name='mentor_management'),

]
