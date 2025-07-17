from shopApp.models import Shop, Reward, Redemption, OpeningHours, Category, RedemptionRequest,Campaign
from childApp.utils.CampaignUtils import CampaignUtils
from teenApp.entities.TaskAssignment import TaskAssignment
from datetime import timedelta
import csv
from Volunteen.constants import CAMPAIGN_TIME_LIMIT_MINUTES
from django.contrib import admin, messages
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from shopApp.utils.shop_manager import ShopManager
from childApp.utils.TeenCoinManager import TeenCoinManager
from django.utils.translation import gettext_lazy as _

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.action(description="Mark selected shops as active")
def activate_shops(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description="Mark selected shops as inactive")
def deactivate_shops(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.display(boolean=True, description="Open Now?")
def is_open_now(obj):
    return obj.is_open()

class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    extra = 1
    fields = ('day', 'opening_hour', 'closing_hour')
    ordering = ('day',)

@admin.action(description="Copy Sunday's hours to all weekdays")
def copy_sunday_hours(modeladmin, request, queryset):
    for shop in queryset:
        sunday_hours = shop.opening_hours.filter(day=6)
        for target_day in range(0, 5):  # Copy to monday-Thursday
            for hour in sunday_hours:
                OpeningHours.objects.update_or_create(
                    shop=shop,
                    day=target_day,
                    opening_hour=hour.opening_hour,
                    defaults={
                        'closing_hour': hour.closing_hour,
                    }
                )

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    inlines = [OpeningHoursInline]
    list_display = ('name', 'city', 'get_category_names', 'is_active', is_open_now)
    list_filter = ('city', 'categories', 'is_active')
    search_fields = ('name',)
    actions = [activate_shops, deactivate_shops, copy_sunday_hours]
@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('title', 'points_required', 'shop', 'is_visible')
    search_fields = ('title', 'shop__name')
    list_filter = ('points_required', 'shop', 'is_visible')

@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ('child', 'points_used', 'date_redeemed', 'shop', 'service_rating', 'reward_rating')
    search_fields = ('child__user__username', 'shop__name')
    list_filter = ('date_redeemed', 'shop', 'service_rating', 'reward_rating')

@admin.register(OpeningHours)
class OpeningHoursAdmin(admin.ModelAdmin):
    list_display = ('shop', 'day', 'opening_hour', 'closing_hour')
    search_fields = ('shop__name',)
    list_filter = ('day', 'shop')
    list_select_related = ('shop',)
    list_display_links = ('shop',)

@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    """Custom admin with a bulk-approval action."""
    list_display  = (
        "id", "child", "reward", "quantity",
        "points_used", "status", "date_requested",
    )
    list_filter   = ("status", "shop")
    search_fields = ("child__user__username", "reward__title")
    actions       = ["approve_requests"]

    @admin.action(description=_("Approve selected redemption requests"))
    def approve_requests(self, request, queryset):
        approved, failed = 0, 0
        queryset = queryset.select_related("child", "reward", "shop")

        for req in queryset:
            if req.status == "approved":
                failed += 1
                continue

            child, shop = req.child, req.shop
            cost = req.quantity * req.reward.points_required
            bal = TeenCoinManager.get_total_active_teencoins(child)
            pts = min(bal, cost)          

            try:
                with transaction.atomic():
                    # debit whatever the child actually has
                    if pts:
                        TeenCoinManager.redeem_teencoins(child, pts)

                    # create redemption with date_redeemed = date_requested
                    redemption = Redemption.objects.create(
                        child=child,
                        reward=req.reward,
                        quantity=req.quantity,
                        points_used=pts,
                        shop=shop,
                    )

                    # Force overwrite date redeemed after creation
                    redemption.date_redeemed = req.date_requested
                    redemption.save(update_fields=["date_redeemed"])
                    shop.unlock_monthly_points(cost)

                    # mark request approved
                    req.status = "approved"
                    req.locked_points = 0
                    req.save(update_fields=["status", "locked_points"])
                    approved += 1

            except Exception as exc:
                self.message_user(request, f"שגיאה בבקשה #{req.pk}: {exc}", level=messages.ERROR)
                failed += 1

        if approved:
            self.message_user(request, f"אושרו {approved} בקשות.", level=messages.SUCCESS)
        if failed:
            self.message_user(request, f"{failed} בקשות נכשלו או דולגו.", level=messages.WARNING)
    
    
@admin.action(description="Activate selected campaigns")
def activate_campaigns(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    messages.success(request, f"{updated} campaign(s) activated.")


@admin.action(description="Deactivate selected campaigns")
def deactivate_campaigns(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    messages.success(request, f"{updated} campaign(s) deactivated.")


@admin.action(description="Export participants to CSV")
def export_participants_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=campaign_participants.csv"
    writer = csv.writer(response)
    writer.writerow(["Campaign Title", "Child Username", "Assigned At"])

    for campaign in queryset:
        assignments = TaskAssignment.objects.filter(task__campaign=campaign)
        for a in assignments:
            writer.writerow([
                campaign.title,
                a.child.user.username,
                a.assigned_at.isoformat(),
            ])
    return response


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "shop",
        "start_date",
        "end_date",
        "max_children",
        "participant_count",
        "is_active",
    )
    list_filter = ("shop", "is_active", "start_date", "end_date")
    search_fields = ("title", "shop__name")
    actions = [activate_campaigns, deactivate_campaigns, export_participants_csv]

    @admin.display(description="Current Participants")
    def participant_count(self, obj):
        return CampaignUtils.current_approved_children_qs(obj).count()