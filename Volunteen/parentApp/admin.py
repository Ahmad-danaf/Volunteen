from django.contrib import admin
from .models import Parent
# Register your models here.


class ParentAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username', 'user__email')

admin.site.register(Parent, ParentAdmin)