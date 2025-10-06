from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class PersonalInfo(models.Model):
    class GenderChoices(models.TextChoices):
        MALE = 'm', 'Male'
        FEMALE = 'f', 'Female'
        UNKNOWN = 'unk', 'Unknown'
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personal_info')
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)
    gender = models.CharField(max_length=10, choices=GenderChoices.choices, default=GenderChoices.UNKNOWN)


    def __str__(self):
        return f"{self.user.username} Personal Info"
