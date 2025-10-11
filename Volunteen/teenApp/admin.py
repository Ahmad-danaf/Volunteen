from django.contrib import admin, messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from teenApp.entities.task import Task, TimeWindowRule,TaskProofRequirement, TaskGroup
from teenApp.entities.recurrence import TaskRecurrence, RecurringRun, Frequency
from django.utils.translation import gettext_lazy as _
from django import forms
from mentorApp.models import Mentor
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from teenApp.models import PersonalInfo
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
User = get_user_model()

class PersonalInfoInline(admin.StackedInline): 
    model = PersonalInfo
    can_delete = False
    verbose_name_plural = 'Personal Info'
    fk_name = 'user'
class UserAdmin(BaseUserAdmin):
    inlines = (PersonalInfoInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_phone')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'personal_info__phone_number')

    def get_phone(self, obj):
        return obj.personal_info.phone_number if hasattr(obj, 'personal_info') else '-'

    get_phone.short_description = 'Phone'



# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('user', 'identifier', 'points')
    search_fields = ('user__username', 'identifier')
    list_filter = ('points',)

class TimeWindowInline(admin.TabularInline):
    model = TimeWindowRule
    extra = 0
    max_num = 2

class TaskRecurrenceInline(admin.StackedInline):
    model = TaskRecurrence
    extra = 0
    can_delete = True
    show_change_link = True
    fieldsets = (
        (None, {
            'fields': ('frequency', 'is_active')
        }),
        (_("Schedule Settings"), {
            'fields': ('interval_days', 'by_weekday', 'day_of_month', 'run_time_local'),
            'classes': ('collapse',)
        }),
        (_("Date Range"), {
            'fields': ('start_date', 'end_date'),
        }),
        (_("Behavior"), {
            'fields': ('deduct_coins_on_create', 'require_sufficient_balance', 'max_instances_per_period'),
            'classes': ('collapse',)
        }),
        (_("Status"), {
            'fields': ('next_run_at', 'last_run_at'),
            'classes': ('collapse',)
        }),
    )
    
@admin.register(TaskGroup)
class TaskGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter  = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'deadline','is_template', 'has_recurrence')
    search_fields = ('title',)
    list_filter = ("deadline", "completed", "groups", "is_template")
    inlines = [TimeWindowInline, TaskRecurrenceInline]
    actions = ["add_to_starter_pack"]

    def has_recurrence(self, obj):
        return hasattr(obj, 'recurrence') and obj.recurrence is not None
    has_recurrence.boolean = True
    has_recurrence.short_description = "Has Recurrence"

    def add_to_starter_pack(self, request, queryset):
        try:
            group = TaskGroup.objects.get(slug="Starter Pack")
        except TaskGroup.DoesNotExist:
            self.message_user(request, "❌ TaskGroup 'Starter Pack' not found. Create it first!", messages.ERROR)
            return

        count = 0
        for task in queryset:
            if group not in task.groups.all():
                task.groups.add(group)
                count += 1
        self.message_user(
            request,
            f"✅ {count} task(s) were added to the Starter Pack group.",
            messages.SUCCESS,
        )

    add_to_starter_pack.short_description = "➕ Add selected tasks to Starter Pack group"

class MentorAdminForm(forms.ModelForm):
    proof_options = forms.MultipleChoiceField(
        choices=TaskProofRequirement.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=_("Allowed Proof Options"),
        help_text=_("Select which proof options this mentor can assign to tasks")
    )

    class Meta:
        model = Mentor
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['proof_options'] = self.instance.allowed_proof_options

    def save(self, commit=True):
        mentor = super().save(commit=False)
        mentor.allowed_proof_options = self.cleaned_data.get('proof_options', [])
        if commit:
            mentor.save()
        return mentor

@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    form = MentorAdminForm
    list_display = ('user', 'available_teencoins', 'get_proof_options')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)

    def get_proof_options(self, obj):
        return ", ".join([dict(TaskProofRequirement.choices).get(opt, opt) for opt in obj.allowed_proof_options])
    get_proof_options.short_description = _("Allowed Proof Options")

    fieldsets = (
        (None, {
            'fields': ('user', 'available_teencoins')
        }),
        (_("Advanced Permissions"), {
            'fields': ('proof_options',),
            'classes': ('collapse', 'wide'),
            'description': _("These settings control special permissions for this mentor")
        }),
    )
@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ('task', 'child', 'assigned_by', 'is_new', 'assigned_at', 'refunded_at')
    search_fields = ('task__title', 'child__user__username', 'assigned_by__username')
    list_filter = ('is_new', 'assigned_at', 'refunded_at')

def assign_remaining_coins(modeladmin, request, queryset):
    updated = 0
    for completion in queryset:
        if completion.task and completion.task.points is not None:
            completion.remaining_coins = completion.task.points + completion.bonus_points
            completion.awarded_coins=completion.task.points
            completion.save()
            updated += 1
    modeladmin.message_user(request, f"{updated} task completions updated with remaining coins.", messages.SUCCESS)   
    
    
def reset_remaining_coins(modeladmin, request, queryset):
    updated = 0
    for completion in queryset:
        completion.remaining_coins = 0
        completion.save()
        updated += 1
    modeladmin.message_user(request, f"{updated} task completions reset with remaining coins.", messages.SUCCESS)
@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('task', 'child', 'completion_date')
    search_fields = ('task__title', 'child__user__username')
    list_filter = ('completion_date',)
    actions = [assign_remaining_coins, reset_remaining_coins]
    
    
@admin.register(TimeWindowRule)
class TimeWindowRuleAdmin(admin.ModelAdmin):
    list_display = ('task', 'window_type', 'specific_date', 'weekday', 'start_time', 'end_time')
    list_filter = ('window_type', 'specific_date', 'weekday')
    search_fields = ('task__title',)

# ======================== RECURRENCE ========================
def run_now_action(modeladmin, request, queryset):
    """Set next_run_at to a few seconds in the future so it runs immediately."""
    updated = queryset.update(next_run_at=timezone.now() + timedelta(seconds=5))
    modeladmin.message_user(request, f"🚀 Scheduled {updated} recurrence(s) to run now.", messages.SUCCESS)
run_now_action.short_description = "▶️ Run now (set next_run_at to now)"

def activate_recurrences(modeladmin, request, queryset):
    """Activate selected recurrences and recalculate next_run_at."""
    updated = 0
    for rec in queryset:
        rec.is_active = True
        rec.save()  
        updated += 1
    modeladmin.message_user(request, f"✅ Activated {updated} recurrence(s).", messages.SUCCESS)
activate_recurrences.short_description = "✅ Activate selected recurrences"

def deactivate_recurrences(modeladmin, request, queryset):
    """Deactivate selected recurrences."""
    updated = queryset.update(is_active=False, next_run_at=None)
    modeladmin.message_user(request, f"⏸️ Deactivated {updated} recurrence(s).", messages.SUCCESS)
deactivate_recurrences.short_description = "⏸️ Deactivate selected recurrences"

@admin.register(TaskRecurrence)
class TaskRecurrenceAdmin(admin.ModelAdmin):
    list_display = ('get_task_title', 'frequency', 'is_active', 'next_run_at', 'last_run_at', 'get_schedule_info')
    list_filter = ('frequency', 'is_active', 'created_at', 'deduct_coins_on_create')
    search_fields = ('task__title',)
    list_select_related = ('task',)
    actions = [run_now_action, activate_recurrences, deactivate_recurrences]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('task', 'frequency', 'is_active')
        }),
        (_("Schedule Settings"), {
            'fields': ('interval_days', 'by_weekday', 'day_of_month', 'run_time_local'),
            'classes': ('collapse',),
            'description': _("Configure based on frequency type")
        }),
        (_("Date Range"), {
            'fields': ('start_date', 'end_date'),
        }),
        (_("Behavior"), {
            'fields': ('deduct_coins_on_create', 'require_sufficient_balance', 'max_instances_per_period'),
            'classes': ('collapse',)
        }),
        (_("Status"), {
            'fields': ('next_run_at', 'last_run_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_task_title(self, obj):
        return obj.task.title
    get_task_title.short_description = 'Task'
    get_task_title.admin_order_field = 'task__title'
    
    def get_schedule_info(self, obj):
        """Display human-readable schedule info."""
        if obj.frequency == Frequency.DAILY:
            return f"Daily at {obj.run_time_local}"
        elif obj.frequency == Frequency.EVERY_X_DAYS:
            return f"Every {obj.interval_days} days at {obj.run_time_local}"
        elif obj.frequency == Frequency.WEEKLY:
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            weekdays = [days[d] for d in (obj.by_weekday or [])]
            return f"Weekly on {', '.join(weekdays)} at {obj.run_time_local}"
        elif obj.frequency == Frequency.MONTHLY:
            return f"Monthly on day {obj.day_of_month} at {obj.run_time_local}"
        return "-"
    get_schedule_info.short_description = 'Schedule'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter tasks to show only templates without recurrence (except current one when editing)."""
        if db_field.name == "task":
            qs = Task.objects.filter(is_template=True, recurrence__isnull=True)
            
            object_id = request.resolver_match.kwargs.get("object_id") if request.resolver_match else None
            if object_id:
                try:
                    current_task_id = TaskRecurrence.objects.get(pk=object_id).task_id
                    qs = Task.objects.filter(
                        Q(is_template=True, recurrence__isnull=True) | 
                        Q(pk=current_task_id, is_template=True)
                    )
                except TaskRecurrence.DoesNotExist:
                    pass
            
            kwargs["queryset"] = qs
            
            # Use a widget that shows template tasks in search
            from django.contrib.admin.widgets import ForeignKeyRawIdWidget
            kwargs["widget"] = ForeignKeyRawIdWidget(db_field.remote_field, admin_site=self.admin_site)
            
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_search_results(self, request, queryset, search_term):
        """Override search to only show recurrences for template tasks."""
        if hasattr(request, 'path') and 'taskrecurrence' in request.path.lower():
            # Filter TaskRecurrence objects where the related task is a template
            queryset = queryset.filter(task__is_template=True)
        return super().get_search_results(request, queryset, search_term)

@admin.register(RecurringRun)
class RecurringRunAdmin(admin.ModelAdmin):
    list_display = ('get_task_title', 'period_start', 'status', 'created_at', 'get_reason_short')
    list_filter = ('status', 'created_at', 'period_start')
    search_fields = ('task_template__title', 'reason')
    list_select_related = ('task_template',)
    date_hierarchy = 'period_start'
    
    readonly_fields = ('task_template', 'period_start', 'status', 'reason', 'created_at')
    
    def get_task_title(self, obj):
        return obj.task_template.title
    get_task_title.short_description = 'Task Template'
    get_task_title.admin_order_field = 'task_template__title'
    
    def get_reason_short(self, obj):
        """Show truncated reason for better display."""
        if not obj.reason:
            return "-"
        return obj.reason[:50] + "..." if len(obj.reason) > 50 else obj.reason
    get_reason_short.short_description = 'Reason'
    
    def has_add_permission(self, request):
        """Prevent manual creation - these are created by the system."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make read-only - these are audit logs."""
        return False

