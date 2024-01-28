
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name=''),
    path('register', views.register, name='register'),
    path('create/',  views.create_task, name='create'),
    path('list/', views.list_view, name='list'),
    path('update/<int:task_id>/', views.update_task, name='update'),
    path('delete/<int:task_id>/', views.delete_task, name='delete'),
    path('complete/<int:task_id>/', views.complete_task, name='complete'),
]