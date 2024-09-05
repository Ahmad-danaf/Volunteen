"""
URL configuration for Volunteen project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from two_factor.urls import urlpatterns as tf_urls
from django.conf.urls.static import static
from . import settings
# Volunteen/urls.py
from django.contrib import admin
from django.urls import path, include
from captcha import urls as captcha_urls  # Import captcha URLs
from two_factor.urls import urlpatterns as tf_urls
# 2FA
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('teenApp.interface_adapters.urls')),
    # Include captcha URLs
    path('captcha/', include(captcha_urls)),
    # 2FA
    path('', include(tf_urls)),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

