from django.db import models
from django.contrib.auth.models import User, Group
from childApp.models import Child
from Volunteen.constants import AVAILABLE_CITIES,SHOP_CATEGORIES
from datetime import timedelta
from django.utils.timezone import now
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
    category = models.CharField(
        max_length=50,
        choices=SHOP_CATEGORIES,
        verbose_name="Category",
        blank=True,
        null=True,
    )    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        shops_group, created = Group.objects.get_or_create(name='Shops')
        self.user.groups.add(shops_group)
        
    def average_service_rating(self):
        ratings = Redemption.objects.filter(shop=self, service_rating__isnull=False).values_list('service_rating', flat=True)
        return round(sum(ratings) / len(ratings), 1) if ratings else None

    def average_reward_rating(self):
        ratings = Redemption.objects.filter(shop=self, reward_rating__isnull=False).values_list('reward_rating', flat=True)
        return round(sum(ratings) / len(ratings), 1) if ratings else None

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
    service_rating = models.IntegerField(null=True, blank=True, verbose_name='Service Rating')  # 1-5 stars
    reward_rating = models.IntegerField(null=True, blank=True, verbose_name='Reward Rating')  # 1-5 stars
    notes = models.TextField(null=True, blank=True, verbose_name='Notes')  # Optional text for additional feedback

    def __str__(self):
        return f'{self.child} redeemed {self.points_used} points at {self.shop} on {self.date_redeemed}'
    
    def can_rate(self):
        """
        Returns True if the redemption can still be rated (within 7 days).
        """
        return self.date_redeemed + timedelta(days=7) >= now()
