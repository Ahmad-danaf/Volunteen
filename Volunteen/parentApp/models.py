from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone

class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    available_teencoins = models.IntegerField(default=50, verbose_name='Available TeenCoins')
    last_monthly_topup = models.DateField(null=True, blank=True, help_text="Date of last monthly top-up")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """
        Automatically add the parent to the 'Parents' group if not already added.
        """
        if not self.last_monthly_topup:
            self.last_monthly_topup = timezone.now().date()
            
        super().save(*args, **kwargs)
        
        parents_group, created = Group.objects.get_or_create(name='Parents')
        self.user.groups.add(parents_group)
        
        
class ChildSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    class Plan(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CREDIT = "CREDIT", "Credit Card"

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    plan = models.CharField(
        max_length=10,
        choices=Plan.choices,
        default=Plan.MONTHLY,
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    
    child = models.OneToOneField(
        'childApp.Child',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name="Child"
    )

    auto_renew = models.BooleanField(
        default=False,
        help_text="If True, subscription will attempt to renew automatically."
    )
    
    start_date = models.DateField()
    end_date = models.DateField()

    canceled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Child Subscription"
        verbose_name_plural = "Child Subscriptions"

    def __str__(self):
        return f"{self.child.user.username} ({self.status})"

    def is_active(self) -> bool:
        """
        Check if the subscription is currently active
        and not past its end_date.
        """
        if self.status != ChildSubscription.Status.ACTIVE:
            return False
        return self.end_date >= timezone.now().date()
    def days_left(self) -> int:
        """
        How many days remain until end_date?
        """
        return (self.end_date - timezone.now().date()).days

    def can_show_expiration_warning(self, days_threshold: int = 7) -> bool:
        """
        Should we show the user a "Subscription expiring soon" banner?
        """
        return not self.auto_renew and self.is_active() and self.days_left() <= days_threshold

    def expire(self) -> None:
        """
        Mark subscription as expired (for daily cron job when end_date passes).
        """
        if self.status != ChildSubscription.Status.EXPIRED:
            self.status = ChildSubscription.Status.EXPIRED
            self.save()

    def cancel(self) -> None:
        """
        Cancel the subscription prior to end_date.
        Typically used if the user manually cancels or requests a stop.
        """
        if self.status == ChildSubscription.Status.ACTIVE:
            self.status = ChildSubscription.Status.CANCELLED
            self.canceled_at = timezone.now()
            self.save()