from django.urls import path
from mentorApp import views

app_name='mentorApp'

urlpatterns = [
    
    path('completed_tasks/', views.mentor_completed_tasks_view, name='mentor_completed_tasks'),
    path('mentor/active-list/', views.mentor_active_list, name='mentor_active_list'), 
    path('mentor/assign-points/', views.assign_points, name='assign_points'),  # Assign points to children
    path('mentor/assign-points/<int:task_id>/', views.assign_points, name='assign_points'),  # Assign points to children for a specific task
    path('mentor/task-list/', views.mentor_task_list, name='mentor_task_list'),
    path('mentor/assign-task/<int:task_id>/', views.assign_task, name='assign_task'),
    path('mentor/assign-points/success/<int:task_id>/', views.points_assigned_success, name='points_assigned_success'),
    path('assign-bonus/', views.assign_bonus, name='assign_bonus'),
    path('ajax/load-children/', views.load_children, name='load_children'),
    path('mentor/edit-task/<int:task_id>/', views.edit_task, name='edit_task'),
    path('mentor/send-whatsapp-message/', views.send_whatsapp_message, name='send_whatsapp_message'),
    path('mentor/', views.mentor_home, name='mentor_home'),  # Mentor home page

]
