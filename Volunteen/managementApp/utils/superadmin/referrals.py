from datetime import datetime, timedelta
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.db import models

from childApp.models import Child, ChildReferral

class ReferralQueryUtils:

    @staticmethod
    def base_qs():
        return (ChildReferral.objects
                .select_related("referred_child", "referrer")
                .order_by("-created_at"))

    @staticmethod
    def filtered_qs(date_from=None, date_to=None, city=None, q=None):
        qs = ReferralQueryUtils.base_qs()
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lt=date_to)
        if city:
            qs = qs.filter(referred_child__city__iexact=city)
        if q:
            # free text search on names / phone / identifier
            qs = qs.filter(
                models.Q(referred_child__user__username__icontains=q) |
                models.Q(referred_child__user__first_name__icontains=q) |
                models.Q(referred_child__user__last_name__icontains=q) |
                models.Q(referred_child__identifier__icontains=q) |
                models.Q(referrer__user__first_name__icontains=q) |
                models.Q(referrer__user__last_name__icontains=q) |
                models.Q(referrer__identifier__icontains=q)
            )
        return qs

    @staticmethod
    def kpis(qs):
        total_referrals = qs.count()
        unique_referrers = qs.values("referrer_id").exclude(referrer__isnull=True).distinct().count()
        unique_referred_children = qs.values("referred_child_id").distinct().count()
        return {
            "total_referrals": total_referrals,
            "unique_referrers": unique_referrers,
            "unique_referred_children": unique_referred_children,
        }

    @staticmethod
    def top_referrers(qs, limit=20):
        # rank referrers by number of referrals
        return (qs.exclude(referrer__isnull=True)
                  .values("referrer_id",
                          "referrer__identifier",
                          "referrer__user__username",
                          "referrer__user__first_name",
                          "referrer__user__last_name",
                          "referrer__city")
                  .annotate(referrals_count=Count("id"))
                  .order_by("-referrals_count")[:limit])

    @staticmethod
    def timeseries_by_day(qs):
        return (qs.annotate(day=TruncDay("created_at"))
                  .values("day")
                  .annotate(count=Count("id"))
                  .order_by("day"))

    @staticmethod
    def city_breakdown(qs, limit=20):
        return (qs.values("referred_child__city")
                  .annotate(count=Count("id"))
                  .order_by("-count")[:limit])

    @staticmethod
    def per_referrer_table(qs):
        # detailed table for all referrers (no limit)
        return (qs.exclude(referrer__isnull=True)
                  .values("referrer_id",
                          "referrer__identifier",
                          "referrer__user__first_name",
                          "referrer__user__last_name",
                          "referrer__city")
                  .annotate(referrals_count=Count("id"))
                  .order_by("-referrals_count", "referrer__user__first_name"))
