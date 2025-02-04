from django.urls import path
from . import views

app_name = 'parentApp'

urlpatterns = [
    path('home/', views.parent_home, name='parent_home'),
    path('home/stats/', views.parent_stats, name='parent_stats'),
    path('child/<int:child_id>/', views.child_detail, name='child_detail'),
    path('child/tasks/<int:child_id>/', views.task_dashboard, name='task_dashboard')
]