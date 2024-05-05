from django.contrib import admin
from .models import Child, Reward, Task, Mentor, Redemption, Shop

# Register the models to the admin interface
@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('user', 'identifier', 'points')
    search_fields = ('user__username', 'identifier')
    list_filter = ('points',)

@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ('title', 'points_required')
    search_fields = ('title',)
    list_filter = ('points_required',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'deadline', 'completed')
    search_fields = ('title',)
    list_filter = ('deadline', 'completed')

@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ('user',)

@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ('child', 'points_used', 'date_redeemed', 'shop')
    search_fields = ('child__user__username', 'reward__title', 'shop__name')
    list_filter = ('date_redeemed', 'shop')

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')
    search_fields = ('name', 'user__username')
    
admin.site.register(Mentor)
