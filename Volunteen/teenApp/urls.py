
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('index', views.index, name='index'),
    path('register', views.register, name='register'),
    path('create/',  views.create_task, name='create'),
    path('list/', views.list_view, name='list'),
    path('update/<int:task_id>/', views.update_task, name='update'),
    path('delete/<int:task_id>/', views.delete_task, name='delete'),
    path('complete/<int:task_id>/', views.complete_task, name='complete'),
    path('reward/', views.reward, name='reward'),
    path('profile/adam/', views.adam_profile, name='adam_profile'),
]