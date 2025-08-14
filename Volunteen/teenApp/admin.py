from django.contrib import admin, messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from teenApp.entities.task import Task, TimeWindowRule,TaskProofRequirement
from django.utils.translation import gettext_lazy as _
from django import forms
from mentorApp.models import Mentor
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from teenApp.models import PersonalInfo
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
    
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'deadline', 'completed')
    search_fields = ('title',)
    list_filter = ('deadline', 'completed')
    inlines = [TimeWindowInline]

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