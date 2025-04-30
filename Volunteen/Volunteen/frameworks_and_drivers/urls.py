from django.contrib import admin
from django.urls import path, include
from captcha import urls as captcha_urls  # Import captcha URLs
from two_factor.urls import urlpatterns as tf_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Default app (teenApp)
    path('', include('teenApp.interface_adapters.urls')),

    # Two-factor authentication
    path('2fa/', include(tf_urls)), 

    # Mentor app
    path('mentor/', include('mentorApp.urls')),

    # Child app
    path('child/', include('childApp.urls')),

    # Shop app
    path('shop/', include('shopApp.urls')),

    # Parent app
    path('parent/', include('parentApp.urls')),
    
    path('institution/', include('institutionApp.urls')),  
    
    # Management app
    path('management/', include('managementApp.urls')),

    # Captcha
    path('captcha/', include(captcha_urls)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

