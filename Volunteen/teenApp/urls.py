
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),
    path('child/', views.child_home, name='child_home'),
    path('mentor/', views.mentor_home, name='mentor_home'),
    path('mentor/points-summary/', views.mentor_points_summary, name='mentor_points_summary'),
    path('shop/', views.shop_home, name='shop_home'),
    #path('index', views.index, name='index'),
    path('register', views.register, name='register'),
    #path('create/',  views.create_task, name='create'),
    path('list/', views.list_view, name='list'),
    path('reward/', views.reward, name='reward'),
    path('redeem/<int:reward_id>/', views.redeem_reward, name='redeem-reward'),
    path('doTask/<int:task_id>/', views.do_task, name='do_task'),
    path('profile/adam/', views.adam_profile, name='adam_profile'),
]