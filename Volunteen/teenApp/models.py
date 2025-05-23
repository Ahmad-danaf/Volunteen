from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PersonalInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personal_info')
    phone_number = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Personal Info"
