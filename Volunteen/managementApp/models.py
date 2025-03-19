from django.db import models
from childApp.models import Child

class DonationCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

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