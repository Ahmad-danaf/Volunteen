from django.contrib.auth.models import User
from django.db import models
from teenApp.entities.child import Child
from teenApp.entities.mentor import Mentor
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.shop import Shop
from teenApp.entities.task import Task
from teenApp.entities.reward import Reward
from teenApp.entities.redemption import Redemption
User.add_to_class('phone', models.CharField(unique=True, max_length=10, blank=True, null=True))
