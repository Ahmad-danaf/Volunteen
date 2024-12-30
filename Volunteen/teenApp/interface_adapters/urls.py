from django.urls import path
from teenApp.interface_adapters.views import (
    LogoutView,
    LandingPageView,
    HomeRedirectView,
    DefaultHomeView,
    TaskListView,
)

app_name = 'teenApp'

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing_page'),
    path('login/', HomeRedirectView.as_view(), name='home_redirect'),  # Redirect users to the appropriate home page
    path('list/', TaskListView.as_view(), name='list'),  # List tasks
    path('default_home/', DefaultHomeView.as_view(), name='default_home'),  # Default home page
    path('logout/', LogoutView.as_view(), name='logout_view'),  # Handle user logout
]
