from django.contrib import admin
from .models import Institution
from parentApp.models import ChildSubscription
from django.utils import timezone
import datetime

@admin.action(description="Activate & Extend All Child Subscriptions")
def activate_and_extend_all_child_subscriptions(modeladmin, request, queryset):
    today = timezone.now().date()
    updated_count = 0
    skipped_count = 0

    for institution in queryset:
        children = institution.children.all()
        for child in children:
            try:
                sub = child.subscription 
            except ChildSubscription.DoesNotExist:
                skipped_count += 1
                continue

            original_end = sub.end_date
            base_date = max(original_end, today)
            added_days = 0

            if sub.plan == ChildSubscription.Plan.MONTHLY:
                added_days = 30
            elif sub.plan == ChildSubscription.Plan.YEARLY:
                added_days = 365
            else:
                modeladmin.message_user(request, f"[SKIP] Unknown plan for {sub}. Skipping.")
                skipped_count += 1
                continue

            sub.end_date = base_date + datetime.timedelta(days=added_days)
            sub.status = ChildSubscription.Status.ACTIVE
            log_line = f"[{today}] Activated via institution admin. Extended {added_days} days (from {original_end} to {sub.end_date})."
            sub.notes = f"{sub.notes or ''}\n{log_line}".strip()
            sub.save()
            updated_count += 1

    modeladmin.message_user(
        request,
        f"[DONE] {updated_count} subscriptions updated. {skipped_count} skipped (no subscription or invalid plan)."
    )
@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    
    list_display = ('name', 'manager', 'total_teencoins', 'available_teencoins')
    search_fields = ('name', 'manager__username')
    list_filter = ('total_teencoins', 'available_teencoins')
    ordering = ('-total_teencoins',)
    actions = [activate_and_extend_all_child_subscriptions]
