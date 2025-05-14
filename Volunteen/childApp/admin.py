from django.contrib import admin
from .models import Medal, StreakMilestoneAchieved

# Register your models here.
admin.site.register(Medal)

@admin.register(StreakMilestoneAchieved)
class StreakMilestoneAchievedAdmin(admin.ModelAdmin):
    list_display = ("child", "streak_day", "achieved_at")
    list_filter = ("streak_day", "achieved_at")
    search_fields = ("child__user__username",)