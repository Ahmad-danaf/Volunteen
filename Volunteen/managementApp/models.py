from django.db import models
from childApp.models import Child
from shopApp.models import Shop
class DonationCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    img = models.ImageField(verbose_name="Image", upload_to='media/images/donation_categories/', null=True, blank=True, default='defaults/no-image.png')

    def __str__(self):
        return self.name

class DonationTransaction(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE)
    category = models.ForeignKey(DonationCategory, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    date_donated = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.child} donated {self.amount} to {self.category}"
    
    
class DonationSpending(models.Model):
    category = models.ForeignKey(DonationCategory, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, null=True, blank=True)
    amount_spent = models.PositiveIntegerField()
    date_spent = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Spent {self.amount_spent} in {self.category.name}"
    
    
class SpendingAllocation(models.Model):
    spending = models.ForeignKey(DonationSpending, on_delete=models.CASCADE)
    transaction = models.ForeignKey(DonationTransaction, on_delete=models.CASCADE)
    amount_used = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.amount_used} spent from {self.transaction}"
