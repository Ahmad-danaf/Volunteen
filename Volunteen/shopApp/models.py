from django.db import models
from django.contrib.auth.models import User, Group
from childApp.models import Child
from Volunteen.constants import AVAILABLE_CITIES,SHOP_CATEGORIES
from datetime import timedelta
from django.utils.timezone import now
from datetime import datetime
from django.utils import timezone

class Category(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    @staticmethod
    def populate_categories():
        """Populate the Category model using SHOP_CATEGORIES from constants.py"""
        for code, name in SHOP_CATEGORIES:
            Category.objects.get_or_create(code=code, name=name)

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
    categories = models.ManyToManyField(Category, related_name="shops", verbose_name="Categories")
    locked_usage_this_month = models.IntegerField(default=0, verbose_name='Locked Points This Month')
    is_active = models.BooleanField(default=True,verbose_name='Is Active', help_text='Uncheck to hide this shop from children and parents')
  
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
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        shops_group, created = Group.objects.get_or_create(name='Shops')
        self.user.groups.add(shops_group)

    def get_category_names(self):
        """Returns a comma-separated string of category names"""
        return ", ".join(category.name for category in self.categories.all())
    
    def is_open(self):
        """
        Returns True if the shop is currently open based on its opening hours.
        """
        now = timezone.localtime(timezone.now())
        current_day = now.weekday()  # Monday is 0, Sunday is 6
        current_time = now.time()
        today_periods = self.opening_hours.filter(day=current_day)

        for period in today_periods:
            start = period.opening_hour
            end = period.closing_hour

            if not start or not end:
                continue

            if start < end:
                if start <= current_time <= end:
                    return True
            else:
                # Overnight case: e.g., 22:00–02:00
                if current_time >= start or current_time <= end:
                    return True

        return False

    def lock_monthly_points(self, points):
        """
        Increase locked_usage_this_month to reflect newly locked points.
        """
        self.locked_usage_this_month += points
        self.save()

    def unlock_monthly_points(self, points):
        """
        Decrease locked_usage_this_month to reflect freed points.
        """
        self.locked_usage_this_month = max(self.locked_usage_this_month - points, 0)
        self.save()

class OpeningHours(models.Model):
    DAYS_OF_WEEK = [
        (0, 'שני'),
        (1, 'שלישי'),
        (2, 'רביעי'),
        (3, 'חמישי'),
        (4, 'שישי'),
        (5, 'שבת'),
        (6, 'ראשון'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="opening_hours")
    day = models.IntegerField(choices=DAYS_OF_WEEK, verbose_name="Day of the Week")
    opening_hour = models.TimeField(verbose_name="Opening Hour", blank=True, null=True)
    closing_hour = models.TimeField(verbose_name="Closing Hour", blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["shop", "day"]),  # Faster queries
        ]

    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK).get(self.day, "Unknown Day")
        return f"{self.shop.name} - {day_name}: {self.opening_hour} to {self.closing_hour}"
    
    
class Reward(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField("Image", upload_to='media/images/', null=True, blank=True, default='defaults/no-image.png')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='rewards')
    is_visible = models.BooleanField(default=True) # show/hide reward from children

    def __str__(self):
        return self.title


class RedemptionRequest(models.Model):
    """
    Stores pending reward requests until approved or rejected by the shop.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    child = models.ForeignKey(Child, on_delete=models.CASCADE, verbose_name='Child')
    shop = models.ForeignKey('shopApp.Shop', on_delete=models.CASCADE, verbose_name='Shop')
    reward = models.ForeignKey('shopApp.Reward', on_delete=models.CASCADE, verbose_name='Reward')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Quantity')
    points_used = models.IntegerField(verbose_name='Total Points Used')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Request Status')
    date_requested = models.DateTimeField(auto_now_add=True, verbose_name='Date Requested')
    locked_points = models.IntegerField(default=0, verbose_name='Locked Points') # Points locked when the request is created
    locked_at = models.DateTimeField(null=True, blank=True, verbose_name='Locked At') # Timestamp when points were locked

    def __str__(self):
        return f'{self.child} requested {self.quantity} x {self.reward.title} at {self.shop}'
    
    def is_expired(self):
        """Check if request has expired (older than 30 minutes)."""
        return self.status == "pending" and self.locked_at and (timezone.now() - self.locked_at) > timedelta(minutes=30)

    
        
class Redemption(models.Model):
    child = models.ForeignKey('childApp.Child', on_delete=models.CASCADE, verbose_name='Child')
    reward = models.ForeignKey('shopApp.Reward', on_delete=models.CASCADE, verbose_name='Reward Used', null=True, blank=True)
    quantity = models.IntegerField(verbose_name='Quantity', null=True, blank=True, default=1)
    points_used = models.IntegerField(verbose_name='Points Used')
    date_redeemed = models.DateTimeField(auto_now_add=True, verbose_name='Date Redeemed')
    shop = models.ForeignKey('shopApp.Shop', on_delete=models.CASCADE, verbose_name='Shop')
    service_rating = models.IntegerField(null=True, blank=True, verbose_name='Service Rating')  # 1-5 stars
    reward_rating = models.IntegerField(null=True, blank=True, verbose_name='Reward Rating')  # 1-5 stars
    notes = models.TextField(null=True, blank=True, verbose_name='Notes')  # Optional text for additional feedback

    def __str__(self):
        return f'{self.child} redeemed {self.points_used} points for {self.reward} at {self.shop} on {self.date_redeemed}'
    
    def can_rate(self):
        """
        Returns True if the redemption can still be rated (within 7 days).
        """
        return self.date_redeemed + timedelta(days=7) >= now()
