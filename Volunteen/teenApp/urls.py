
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_redirect, name='home_redirect'),
    path('child/', views.child_home, name='child_home'),
    path('mentor/', views.mentor_home, name='mentor_home'),
    path('mentor/points-summary/', views.mentor_points_summary, name='mentor_points_summary'),
    path('list/', views.list_view, name='list'),
    path('reward/', views.reward, name='reward'),
    path('shop_redeem/', views.redeem_points, name='redeem_points'),
    path('shop_home/', views.shop_home, name='shop_home'),


]