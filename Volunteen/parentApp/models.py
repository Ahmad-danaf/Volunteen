from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    available_teencoins = models.IntegerField(default=50, verbose_name='Available TeenCoins')
    last_monthly_topup = models.DateField(null=True, blank=True, help_text="Date of last monthly top-up")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """
        Automatically add the parent to the 'Parents' group if not already added.
        """
        if not self.last_monthly_topup:
            self.last_monthly_topup = timezone.now().date()
            
        super().save(*args, **kwargs)
        
        parents_group, created = Group.objects.get_or_create(name='Parents')
        self.user.groups.add(parents_group)