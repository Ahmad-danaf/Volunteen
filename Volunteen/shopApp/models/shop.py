
from django.db import models
from django.contrib.auth.models import User, Group
import uuid
from django.utils.timezone import now
from django.utils import timezone

from Volunteen.constants import AVAILABLE_CITIES,SHOP_CATEGORIES
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
    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True, 
        db_index=True,
    )
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
    address = models.CharField(max_length=255, verbose_name="Address", blank=True, null=True)
    google_map_embed = models.TextField(verbose_name="Google Maps Embed HTML", blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        shops_group, created = Group.objects.get_or_create(name='Shops')
        self.user.groups.add(shops_group)
        
    def rotate_public_id(self):
        """Force-generate a new UUID (only when explicitly called)."""
        self.public_id = uuid.uuid4()
        self.save(update_fields=["public_id"])
        
    def average_service_rating(self):
        ratings = Redemption.objects.filter(shop=self, service_rating__isnull=False).values_list('service_rating', flat=True)
        return round(sum(ratings) / len(ratings), 1) if ratings else None

    def average_reward_rating(self):
        ratings = Redemption.objects.filter(shop=self, reward_rating__isnull=False).values_list('reward_rating', flat=True)
        return round(sum(ratings) / len(ratings), 1) if ratings else None

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
    