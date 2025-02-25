from django.contrib import admin
from .models import Shop, Reward, Redemption, OpeningHours, Category, RedemptionRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'get_category_names')
    list_filter = ('city', 'categories')
    search_fields = ('name',)

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

def make_pending(modeladmin, request, queryset):
    queryset.update(status='pending')
make_pending.short_description = "Mark selected requests as pending"

@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    list_display = ('child', 'reward', 'status', 'date_requested')
    search_fields = ('child__user__username', 'reward__title')
    list_filter = ('status', 'date_requested')
    list_select_related = ('child', 'reward')
    list_display_links = ('child', 'reward')
    actions = [make_pending]