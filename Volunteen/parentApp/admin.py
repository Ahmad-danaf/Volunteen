from django.contrib import admin
from django import forms
from .models import Parent,ChildSubscription
from django.utils import timezone
import datetime

class ParentAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username', 'user__email')

admin.site.register(Parent, ParentAdmin)

@admin.action(description="Make subscription active and extend based on plan")
def make_active_and_extend(modeladmin, request, queryset):
    today = timezone.now().date()
    count = 0

    for sub in queryset:
        original_end = sub.end_date
        added_days = 0

        # Determine base date to extend from
        base_date = max(original_end, today)

        # Decide how many days to add
        if sub.plan == ChildSubscription.Plan.MONTHLY:
            added_days = 30 
        elif sub.plan == ChildSubscription.Plan.YEARLY:
            added_days = 365
        else:
            modeladmin.message_user(request, f"[SKIP] Unknown plan for {sub}. Skipping.")
            continue

        sub.end_date = base_date + datetime.timedelta(days=added_days)
        sub.status = ChildSubscription.Status.ACTIVE

        log_line = f"[{today.strftime('%Y-%m-%d')}] Marked ACTIVE via admin panel. Extended {added_days} days (from {original_end} to {sub.end_date})."
        sub.notes = f"{sub.notes or ''}\n{log_line}".strip()
        sub.save()
        count += 1

    modeladmin.message_user(request, f"[SUC] {count} subscriptions updated successfully.")


@admin.action(description="Set payment method to CASH (auto-renew OFF)")
def mark_as_cash(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = 0
    for sub in queryset:
        sub.payment_method = ChildSubscription.PaymentMethod.CASH
        sub.auto_renew = False
        sub.notes = f"{sub.notes or ''}\n[{today}] Changed payment method to CASH via admin (auto-renew OFF)".strip()
        sub.save()
        updated += 1
    modeladmin.message_user(request, f"[SUC] Updated {updated} subscriptions to CASH")


@admin.action(description="Set payment method to CREDIT (auto-renew ON)")
def mark_as_credit(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = 0
    for sub in queryset:
        sub.payment_method = ChildSubscription.PaymentMethod.CREDIT
        sub.auto_renew = True
        sub.notes = f"{sub.notes or ''}\n[{today}] Changed payment method to CREDIT via admin (auto-renew ON)".strip()
        sub.save()
        updated += 1
    modeladmin.message_user(request, f"[SUC] Updated {updated} subscriptions to CREDIT")


@admin.action(description="Set plan to MONTHLY")
def set_plan_monthly(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = 0
    for sub in queryset:
        old_plan = sub.plan
        sub.plan = ChildSubscription.Plan.MONTHLY
        sub.notes = f"{sub.notes or ''}\n[{today}] Plan changed from {old_plan} to MONTHLY via admin.".strip()
        sub.save()
        updated += 1
    modeladmin.message_user(request, f"[SUC] Updated {updated} subscriptions to MONTHLY")


@admin.action(description="Set plan to YEARLY")
def set_plan_yearly(modeladmin, request, queryset):
    today = timezone.now().date()
    updated = 0
    for sub in queryset:
        old_plan = sub.plan
        sub.plan = ChildSubscription.Plan.YEARLY
        sub.notes = f"{sub.notes or ''}\n[{today}] Plan changed from {old_plan} to YEARLY via admin.".strip()
        sub.save()
        updated += 1
    modeladmin.message_user(request, f"[SUC] Updated {updated} subscriptions to YEARLY")

class ChildSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('child', 'status', 'start_date', 'end_date', 'plan', 'payment_method')
    search_fields = ('child__user__username', 'child__user__email')
    list_filter = ('status', 'plan', 'payment_method')
    actions = [make_active_and_extend,mark_as_cash,mark_as_credit,set_plan_monthly,set_plan_yearly]


admin.site.register(ChildSubscription, ChildSubscriptionAdmin)
