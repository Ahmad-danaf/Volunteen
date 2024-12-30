from django.urls import path
from mentorApp.views import (
    MentorHomeView,
    MentorChildrenDetailsView,
    MentorCompletedTasksView,
    AddTaskView,
    EditTaskView,
    MentorActiveListView,
    MentorTaskListView,
    AssignTaskView,
    AssignPointsView,
    PointsAssignedSuccessView,
    SendWhatsAppMessageView,
    AssignBonusView,
LoadChildrenView
    
)
app_name = 'mentorApp'
urlpatterns = [
    path('home/', MentorHomeView.as_view(), name='mentor_home'),
    path('children-details/', MentorChildrenDetailsView.as_view(), name='mentor_children_details'),
    path('completed-tasks/', MentorCompletedTasksView.as_view(), name='mentor_completed_tasks'),
    path('add-task/', AddTaskView.as_view(), name='add_task'),
    path('edit-task/<int:task_id>/', EditTaskView.as_view(), name='edit_task'),
     path('assign-bonus/', AssignBonusView.as_view(), name='assign_bonus'),
    path('active-tasks/', MentorActiveListView.as_view(), name='mentor_active_list'),
    path('task-list/', MentorTaskListView.as_view(), name='mentor_task_list'),
    path('assign-task/<int:task_id>/', AssignTaskView.as_view(), name='assign_task'),
    path('assign-points/<int:task_id>/', AssignPointsView.as_view(), name='assign_points'),
    path('points-assigned/<int:task_id>/', PointsAssignedSuccessView.as_view(), name='points_assigned_success'),
    path('send-whatsapp/', SendWhatsAppMessageView.as_view(), name='send_whatsapp_message'),
    path('ajax/load-children/', LoadChildrenView.as_view(), name='load_children'),
]
