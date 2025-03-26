from django.urls import path
from mentorApp import views

app_name='mentorApp'

urlpatterns = [
    path('home/', views.mentor_home, name='mentor_home'),  # Mentor home page
    path('assign-points/', views.assign_points, name='assign_points'),  # Assign points to children
    path('assign-points/<int:task_id>/', views.assign_points, name='assign_points'),  # Assign points to children for a specific task
    path('task-list/', views.mentor_task_list, name='mentor_task_list'),
    path('add-task/', views.add_task, name='mentor_add_task'),
    path('duplicate-task/<int:task_id>/', lambda request, task_id: views.add_task(request, task_id, duplicate=True), name='mentor_duplicate_task'),  # Duplicate a task
    path('assign-task/<int:task_id>/', views.assign_task, name='assign_task'),
    path('assign-points/success/<int:task_id>/', views.points_assigned_success, name='points_assigned_success'),
    path('edit-task/<int:task_id>/', views.edit_task, name='edit_task'),
    path('send-whatsapp-message/', views.send_whatsapp_message, name='send_whatsapp_message'),
    path('mentor_children_details/', views.mentor_children_details, name='mentor_children_details'),
    path('mentor_task_images/', views.mentor_task_images, name='mentor_task_images'),
    path('review_task/', views.review_task, name='review_task'),
    path('templates/', views.template_list, name='template_list'),
    path('templates/remove/<int:task_id>/', views.remove_from_templates, name='remove_from_templates'),
    path('bonus/', views.bonus_child_selection, name='bonus_child_selection'),
    path('bonus/<int:child_id>/', views.child_bonus_detail, name='child_bonus_detail'),
    path('bonus/assign/<int:task_completion_id>/', views.assign_bonus, name='assign_bonus'),
    path('children_performance/', views.children_performance, name='children_performance'),

]
