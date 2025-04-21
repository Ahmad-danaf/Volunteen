from django.db import models

class Campaign(models.Model):
    shop       = models.ForeignKey('shopApp.Shop', on_delete=models.CASCADE, related_name="campaigns")
    title         = models.CharField(max_length=120)
    description   = models.TextField(blank=True)
    banner_img    = models.ImageField(upload_to="campaign_banners/", blank=True, null=True)

    start_date    = models.DateField()
    end_date      = models.DateField()

    max_children  = models.PositiveIntegerField(default=0)   # 0 = unlimited
    reward_title  = models.CharField(max_length=100, blank=True)  # e.g. “10 % coupon”
    is_active     = models.BooleanField(default=True)

    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop.name}: {self.title}"

