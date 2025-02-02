from django.contrib import admin
from .models import Shop, Reward, Redemption, OpeningHours, Category

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