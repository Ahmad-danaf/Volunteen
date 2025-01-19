from django.urls import path
from . import views

app_name = 'parentApp'

urlpatterns = [
    path('home/', views.parent_home, name='parent_home'),
]