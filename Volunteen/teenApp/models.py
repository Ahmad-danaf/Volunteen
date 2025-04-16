from django.contrib.auth.models import User
from django.db import models
import os

if not os.environ.get('VOLUNTEEN_CI_NO_PHONE', 'false') == 'true':
    User.add_to_class('phone', models.CharField(unique=True, max_length=10, blank=True, null=True))
