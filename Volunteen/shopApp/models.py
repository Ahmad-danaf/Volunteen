from django.db import models
from django.contrib.auth.models import User, Group
from childApp.models import Child
from Volunteen.constants import AVAILABLE_CITIES
class Shop(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    max_points = models.IntegerField(default=1000, verbose_name='Max Points')
    img = models.ImageField("Image", upload_to='media/images/', null=True, blank=True)
    city = models.CharField(
        max_length=3,
        choices=AVAILABLE_CITIES,
        verbose_name="City",
        blank=True,
        null=True,
    )    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        shops_group, created = Group.objects.get_or_create(name='Shops')
        self.user.groups.add(shops_group)

class OpeningHours(models.Model):
    DAYS_OF_WEEK = [
        (0, 'ראשון'),
        (1, 'שני'),
        (2, 'שלישי'),
        (3, 'רביעי'),
        (4, 'חמישי'),
        (5, 'שישי'),
        (6, 'שבת'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="opening_hours")
    day = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="Day of the Week")
    opening_hour = models.TimeField(verbose_name="Opening Hour", blank=True, null=True)
    closing_hour = models.TimeField(verbose_name="Closing Hour", blank=True, null=True)

    class Meta:
        unique_together = ('shop', 'day')  # Ensure each shop has only one schedule per day

    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK).get(self.day, "Unknown Day")
        return f"{self.shop.name} - {day_name}: {self.opening_hour} to {self.closing_hour}"
    
    
class Reward(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField("Image", upload_to='media/images/', null=True, blank=True, default='defaults/no-image.png')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='rewards')
    is_visible = models.BooleanField(default=True)  

    def __str__(self):
        return self.title


class Redemption(models.Model):
    child = models.ForeignKey('childApp.Child', on_delete=models.CASCADE, verbose_name='Child')
    points_used = models.IntegerField(verbose_name='Points Used')
    date_redeemed = models.DateTimeField(auto_now_add=True, verbose_name='Date Redeemed')
    shop = models.ForeignKey('shopApp.Shop', on_delete=models.CASCADE, verbose_name='Shop')

    def __str__(self):
        return f'{self.child} redeemed {self.points_used} points at {self.shop} on {self.date_redeemed}'
