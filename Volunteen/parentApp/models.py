from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    available_teencoins = models.IntegerField(default=0, verbose_name='Available TeenCoins')
    
    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """
        Automatically add the parent to the 'Parents' group if not already added.
        """
        super().save(*args, **kwargs)
        parents_group, created = Group.objects.get_or_create(name='Parents')
        self.user.groups.add(parents_group)