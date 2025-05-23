"""
Django settings for Volunteen project.

Generated by 'django-admin startproject' using Django 5.0.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()
import sys
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == 'test'

# Build paths inside the project like this: BASE_DIR / 'subdir'.

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
BASE_DIR = Path(__file__).resolve().parent.parent
# SECURITY WARNING: keep the secret key used in production secret!

# SECURITY WARNING: don't run with debug turned on in production!

SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
development = os.getenv("DEVELOPMENT","False") == "True"
DEBUG = development
ALLOWED_HOSTS = ['volunteen.site', 'www.volunteen.site', 'localhost', '127.0.0.1', '51.21.38.172',"Volunteen.pythonanywhere.com","*"]
if development:
    INTERNAL_IPS = ["127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'institutionApp',
    'parentApp',
    'teenApp',
    'childApp',
    'shopApp',
    'mentorApp',
    'managementApp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_q',
    'captcha',
    'widget_tweaks',
    
    # 2FA
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'crispy_bootstrap4',
    'crispy_forms',
    
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

# #2FA
# LOGIN_URL = 'two_factor:login'
# LOGIN_REDIRECT_URL = 'teenApp:home_redirect'

LOGIN_URL = 'teenApp:login'
LOGIN_REDIRECT_URL = 'teenApp:home_redirect'
LOGOUT_REDIRECT_URL = 'teenApp:landing_page'



# reCAPTCHA keys 
RECAPTCHA_PUBLIC_KEY = '6LetRF4pAAAAAMssM8IvwXNDeLq5JfhPQf79Wa_1' 
RECAPTCHA_PRIVATE_KEY = '6LetRF4pAAAAAIyO-TaXHs6dlpDbJQ4DAJAErifT'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware', # 2FA

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Volunteen.frameworks_and_drivers.urls'
template_name='two_factor/login.html'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'teenApp', 'templates')],  # נתיב לתיקיית התבניות
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'Volunteen.frameworks_and_drivers.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DATABASE_NAME'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': os.getenv('DATABASE_PORT'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_TZ = True
TIME_ZONE = 'Asia/Jerusalem'

USE_I18N = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/


CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1','https://www.volunteen.site', 'http://localhost']



STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
if development:
    STATIC_ROOT = None # for development
else:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # for production





MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media', 'media')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if development and not RUNNING_TESTS:
    print("#############we are in development#############")
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INSTALLED_APPS += ['debug_toolbar']
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: True,
        "SHOW_COLLAPSED": True,
    }

CSRF_FAILURE_VIEW = 'teenApp.interface_adapters.views.csrf_failure_view'



Q_CLUSTER = {
    'name': 'volunteen_qcluster',
    'workers': 6,   # number of workers
    'recycle': 300,  
    'timeout': 30,  
    'retry': 120,  
    'queue_limit': 100, 
    'bulk': 10,  
    'poll': 0.3,  
    'orm': 'default',  # Use Django ORM as broker
    "sync": False,
}
