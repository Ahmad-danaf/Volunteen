from django.urls import path
from teenApp.interface_adapters import views

app_name = 'teenApp'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('login/', views.home_redirect, name='home_redirect'),  # Redirects users to the appropriate home page
    path('list/', views.list_view, name='list'),  # List tasks from external API
    path('default_home/', views.default_home, name='default_home'),  # Default home page
    path('logout/', views.logout_view, name='logout_view'),  # Handle user logout
]
