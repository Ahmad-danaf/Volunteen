from django.db import models
from django.contrib.auth.models import User, Group
from Volunteen.constants import AVAILABLE_CITIES,SHOP_CATEGORIES
from datetime import datetime
from .rewards import Redemption

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
    