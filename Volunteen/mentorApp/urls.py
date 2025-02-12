from django.urls import path
from mentorApp import views

app_name='mentorApp'

urlpatterns = [
    
    path('home/', views.mentor_home, name='mentor_home'),  # Mentor home page
    path('completed_tasks/', views.mentor_completed_tasks_view, name='mentor_completed_tasks'),
    path('active-list/', views.mentor_active_list, name='mentor_active_list'), 
    path('assign-points/', views.assign_points, name='assign_points'),  # Assign points to children
    path('assign-points/<int:task_id>/', views.assign_points, name='assign_points'),  # Assign points to children for a specific task
    path('task-list/', views.mentor_task_list, name='mentor_task_list'),
    path('add-task/', views.add_task, name='mentor_add_task'),
    path('assign-task/<int:task_id>/', views.assign_task, name='assign_task'),
    path('assign-points/success/<int:task_id>/', views.points_assigned_success, name='points_assigned_success'),
    path('assign-bonus/', views.assign_bonus, name='assign_bonus'),
    path('ajax/load-children/', views.load_children, name='load_children'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit_task'),
    path('send-whatsapp-message/', views.send_whatsapp_message, name='send_whatsapp_message'),
    path('mentor_children_details/', views.mentor_children_details, name='mentor_children_details'),
    path('mentor_task_images/', views.mentor_task_images, name='mentor_task_images'),
    path('review_task/', views.review_task, name='review_task'),
]
