from django.contrib import admin
from .models import Medal, StreakMilestoneAchieved,ChildBan
from django.utils import timezone
from django.db import models


# Register your models here.
admin.site.register(Medal)

@admin.register(StreakMilestoneAchieved)
class StreakMilestoneAchievedAdmin(admin.ModelAdmin):
    list_display = ("child", "streak_day", "achieved_at")
    list_filter = ("streak_day", "achieved_at")
    search_fields = ("child__user__username",)
    
    
class IsActiveFilter(admin.SimpleListFilter):
    title = 'active status'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'active':
            return queryset.filter(
                revoked_at__isnull=True,
                starts_at__lte=now,
            ).filter(
                models.Q(ends_at__isnull=True) | 
                models.Q(ends_at__gt=now)
            )
        elif self.value() == 'inactive':
            return queryset.exclude(
                revoked_at__isnull=True,
                starts_at__lte=now,
            ).exclude(
                models.Q(ends_at__isnull=True) | 
                models.Q(ends_at__gt=now)
            )

@admin.register(ChildBan)
class ChildBanAdmin(admin.ModelAdmin):
    list_display = (
        'child',
        'scope',
        'starts_at',
        'ends_at',
        'is_active_flag',
        'note_child',
        'created_by',
        'created_at'
    )
    list_filter = (
        IsActiveFilter,
        'scope',
        'starts_at',
        'ends_at',
    )
    search_fields = (
        'child__user__username',  
        'note_child',
        'note_staff',
    )
    raw_id_fields = ('child', 'created_by', 'revoked_by')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': (
                'child',
                'scope',
                ('starts_at', 'ends_at'),
                'severity'
            )
        }),
        ('Notes', {
            'fields': (
                'note_child',
                'note_staff'
            )
        }),
        ('Revocation', {
            'fields': (
                'revoked_at',
                'revoked_by',
                'revoke_reason'
            ),
            'classes': ('collapse',)
        }),
    )

    def is_active_flag(self, obj):
        return obj.is_active
    is_active_flag.boolean = True
    is_active_flag.short_description = 'Active'

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # New ban being created
            obj.created_by = request.user
        super().save_model(request, obj, form, change)