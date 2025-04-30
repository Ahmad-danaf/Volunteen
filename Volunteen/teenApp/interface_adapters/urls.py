from django.urls import path
from teenApp.interface_adapters import views
from django.contrib.auth import views as auth_views

app_name = 'teenApp'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('login/', auth_views.LoginView.as_view(template_name='two_factor/login.html'), name='login'),
    path('home_redirect/', views.home_redirect, name='home_redirect'),
    path('list/', views.list_view, name='list'),
    path('default_home/', views.default_home, name='default_home'),
    path('logout/', views.logout_view, name='logout_view'),
]

