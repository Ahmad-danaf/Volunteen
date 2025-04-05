from django.contrib import admin, messages
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.models import Child
from teenApp.entities.task import Task
from mentorApp.models import Mentor
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
# Define a new User admin
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_phone')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')

    def get_phone(self, instance):
        return instance.phone
    get_phone.short_description = 'Phone'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

class CustomUserAdmin(BaseUserAdmin):
    # Include the 'phone' field in the fieldsets to add it to the user form in the admin panel
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('phone',)}),
    )
    
    list_display = BaseUserAdmin.list_display + ('phone',)

# Unregister the original User admin
admin.site.unregister(User)
# Register the User model with the new CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('user', 'identifier', 'points')
    search_fields = ('user__username', 'identifier')
    list_filter = ('points',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'points', 'deadline', 'completed')
    search_fields = ('title',)
    list_filter = ('deadline', 'completed')

@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ('user',)


def assign_remaining_coins(modeladmin, request, queryset):
    updated = 0
    for completion in queryset:
        if completion.task and completion.task.points is not None:
            completion.remaining_coins = completion.task.points + completion.bonus_points
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