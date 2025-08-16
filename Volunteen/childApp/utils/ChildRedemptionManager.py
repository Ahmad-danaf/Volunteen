from django.utils.timezone import now, timedelta
from django.db.models import Sum, Count, Q
from shopApp.models import Redemption, Shop, RedemptionRequest
from django.shortcuts import get_object_or_404
from childApp.models import BanScope,DEFAULT_BAN_NOTES,ChildBan
from django.utils import timezone

class ChildRedemptionManager:

    @staticmethod
    def get_all_redemptions(child):
        """Retrieve all redemptions made by the child."""
        return Redemption.objects.filter(child=child).order_by("-date_redeemed")

    @staticmethod
    def get_redemptions_in_date_range(child, start_date, end_date):
        """Retrieve redemptions within a specific date range."""
        return Redemption.objects.filter(child=child, date_redeemed__range=(start_date, end_date))

    @staticmethod
    def get_redemptions_by_shop(child, shop):
        """Retrieve all redemptions made at a specific shop."""
        return Redemption.objects.filter(child=child, shop=shop)

    @staticmethod
    def get_recent_redemptions(child, days=30):
        """Retrieve redemptions made in the last `days` days (default: 30)."""
        recent_date = now() - timedelta(days=days)
        return Redemption.objects.filter(child=child, date_redeemed__gte=recent_date)

    @staticmethod
    def get_total_points_spent(child):
        """Retrieve the total number of points spent by the child across all redemptions."""
        return Redemption.objects.filter(child=child).aggregate(total=Sum('points_used'))['total'] or 0

    @staticmethod
    def get_points_spent_in_month(child, month, year):
        """Retrieve the total points spent by the child in a specific month and year."""
        return Redemption.objects.filter(
            child=child,
            date_redeemed__month=month,
            date_redeemed__year=year
        ).aggregate(total=Sum('points_used'))['total'] or 0

    @staticmethod
    def get_daily_spent_points(child):
        """Retrieve the total points spent by the child today."""
        today = now().date()
        return Redemption.objects.filter(child=child, date_redeemed__date=today).aggregate(total=Sum('points_used'))['total'] or 0

    @staticmethod
    def can_rate_redemption(child, redemption):
        """Check if the child can still rate a redemption (within 7 days of purchase)."""
        return redemption.child == child and redemption.can_rate()

    @staticmethod
    def update_redemption_rating(child, redemption_id, service_rating, reward_rating):
        """Update the rating for a redemption, if allowed."""
        redemption = get_object_or_404(Redemption, id=redemption_id, child=child)

        if not redemption.can_rate():
            return {"status": "error", "message": "דירוג אינו אפשרי לאחר 7 ימים מהקנייה."}

        redemption.service_rating = service_rating
        redemption.reward_rating = reward_rating
        redemption.save()

        return {"status": "success", "message": "הדירוג עודכן בהצלחה!"}

    @staticmethod
    def get_most_frequent_shops(child, limit=5):
        """Retrieve the shops where the child redeems rewards most frequently."""
        return Redemption.objects.filter(child=child).values('shop__name').annotate(
            count=Count('shop')
        ).order_by('-count')[:limit]

    @staticmethod
    def get_teen_coins_used(child):
        """Retrieve the total number of teen coins used by the child."""
        return Redemption.objects.filter(child=child).aggregate(total=Sum('points_used'))['total'] or 0
    
    @staticmethod
    def get_not_approved_requests(child):
        """Retrieve all pending requests for the child."""
        return RedemptionRequest.objects.filter(
            child=child
        ).exclude(status="approved").order_by("-date_requested")
    
    @staticmethod
    def active_purchase_ban(child, at=None):
        """
        Return the active purchase-ban record for this child (PURCHASE or ALL).
        Returns None if no ban is active.
        """
        now = at or timezone.now()
        return (
            ChildBan.objects
            .filter(
                child=child,
                scope__in=[BanScope.PURCHASE, BanScope.ALL],
                revoked_at__isnull=True,
                starts_at__lte=now,
            )
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def is_banned_for_purchases(child, at=None) -> bool:
        """Return True if the child currently has an active purchase ban."""
        return ChildRedemptionManager.active_purchase_ban(child, at=at) is not None

    @staticmethod
    def get_ban_note(child, at=None) -> str:
        """Return the note_child of the active purchase ban (or '')."""
        ban = ChildRedemptionManager.active_purchase_ban(child, at=at)
        return ban.note_child if ban else ""
