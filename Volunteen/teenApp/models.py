from django.contrib.auth.models import User
from django.db import models
User.add_to_class('phone', models.CharField(unique=True, max_length=10, blank=True, null=True))
