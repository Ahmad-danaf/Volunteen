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
        now = datetime.now()
        current_day = now.weekday()  # Monday is 0, Sunday is 6
        current_time = now.time()

        try:
            # Get today's opening hours
            opening_hours = self.opening_hours.get(day=current_day)
            
            # If no opening hours exist for today, assume closed
            if not opening_hours:
                return False

            # Handle shops that are open past midnight
            if opening_hours.opening_hour and opening_hours.closing_hour:
                if opening_hours.opening_hour < opening_hours.closing_hour:
                    # Normal case: opening and closing on same day
                    return opening_hours.opening_hour <= current_time <= opening_hours.closing_hour
                else:
                    # Special case: closing time is next day (e.g., 22:00-02:00)
                    return current_time >= opening_hours.opening_hour or current_time <= opening_hours.closing_hour

        except OpeningHours.DoesNotExist:
            # No opening hours defined for this day
            return False

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
