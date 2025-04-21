from django.db import models
from childApp.models import Child
from datetime import timedelta
from django.utils.timezone import now
from datetime import datetime
from django.utils import timezone

    
class Reward(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(verbose_name='Reward Description', help_text='Enter the reward details')
    points_required = models.IntegerField(verbose_name='Points Required', help_text='Enter the points required for this reward')
    img = models.ImageField("Image", upload_to='media/images/', null=True, blank=True, default='defaults/no-image.png')
    shop = models.ForeignKey('shopApp.Shop', on_delete=models.CASCADE, related_name='rewards')
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
