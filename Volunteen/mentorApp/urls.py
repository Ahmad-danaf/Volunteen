from django.urls import path
from mentorApp.views import core, recurrence, task_groups

app_name='mentorApp'

urlpatterns = [
    path('home/', core.mentor_home, name='mentor_home'),  # Mentor home page
    path('assign-points/', core.assign_points, name='assign_points'),  # Assign points to children
    path('assign-points/<int:task_id>/', core.assign_points, name='assign_points'),  # Assign points to children for a specific task
    path('task-list/', core.mentor_task_list, name='mentor_task_list'),
    path('add-task/', core.add_task, name='mentor_add_task'),
    path('duplicate-task/<int:task_id>/', lambda request, task_id: core.add_task(request, task_id, duplicate=True), name='mentor_duplicate_task'),  # Duplicate a task
    path('assign-task/<int:task_id>/', core.assign_task, name='assign_task'),
    path('assign-points/success/<int:task_id>/', core.points_assigned_success, name='points_assigned_success'),
    path('edit-task/<int:task_id>/', core.edit_task, name='edit_task'),
    path('send-whatsapp-message/', core.send_whatsapp_message, name='send_whatsapp_message'),
    path('mentor_children_details/', core.mentor_children_details, name='mentor_children_details'),
    path('mentor_task_images/', core.mentor_task_images, name='mentor_task_images'),
    path('review_task/', core.review_task, name='review_task'),
    path('templates/', core.template_list, name='template_list'),
    path('templates/remove/<int:task_id>/', core.remove_from_templates, name='remove_from_templates'),
    path('bonus/', core.bonus_task_selection, name='bonus_task_selection'),
    path('bonus/<int:task_id>/', core.bonus_children_selection, name='bonus_children_selection'),
    path('bonus/assign/<int:task_id>/', core.assign_bonus_multi, name='assign_bonus_multi'),
    path('children_performance/', core.children_performance, name='children_performance'),
    path('groups/', core.mentor_group_list, name='mentor_group_list'),
    path('groups/create/', core.mentor_group_create, name='mentor_group_create'),
    path('groups/<int:group_id>/edit/', core.mentor_group_edit, name='mentor_group_edit'),
    path('groups/<int:group_id>/toggle/', core.mentor_group_toggle_active, name='mentor_group_toggle_active'),
    path('groups/<int:group_id>/delete/', core.mentor_group_delete, name='mentor_group_delete'), 
    
    path("recurrence_dashboard/", recurrence.recurrence_dashboard_page, name="recurrence_dashboard"),
    path("template/<int:task_id>/create_recurrence/", recurrence.create_recurrence, name="create_task_recurrence"),
    path("recurrences/", recurrence.recurrence_list, name="recurrence_list"),
    path("recurrences/<int:rec_id>/", recurrence.recurrence_detail, name="recurrence_detail"),
    path("recurrences/<int:rec_id>/toggle/", recurrence.recurrence_toggle_active, name="recurrence_toggle"),
    path("recurrences/<int:rec_id>/update/", recurrence.recurrence_update, name="recurrence_update"),
    path("recurrences/<int:rec_id>/delete/", recurrence.recurrence_delete, name="recurrence_delete"),
    path("recurrences/<int:rec_id>/runs/", recurrence.recurrence_runs, name="recurrence_runs"),
    
    # TaskGroup URLs
    path('task-groups/', task_groups.task_group_dashboard, name='task_group_dashboard'),
    path('task-groups/add-task-to-group/', task_groups.add_task_to_group, name='add_task_to_group'),
    path('task-groups/create/', task_groups.create_task_group, name='create_task_group'),
    path('task-groups/<int:group_id>/', task_groups.task_group_detail, name='task_group_detail'),
    path('task-groups/<int:group_id>/edit/', task_groups.edit_task_group, name='edit_task_group'),
    path('task-groups/<int:group_id>/delete/', task_groups.delete_task_group, name='delete_task_group'),
    path('task-groups/<int:group_id>/add-children/', task_groups.add_children_to_group, name='add_children_to_group'),
    path('task-groups/<int:group_id>/remove-child/<int:child_id>/', task_groups.remove_child_from_group, name='remove_child_from_group'),
    path('task-groups/<int:group_id>/search-children/', task_groups.search_children_ajax, name='search_children_ajax'),
]
