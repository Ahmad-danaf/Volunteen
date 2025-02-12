from django.contrib import admin
from .models import Institution

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'total_teencoins', 'available_teencoins')
    search_fields = ('name', 'manager__username')
    list_filter = ('total_teencoins', 'available_teencoins')
    ordering = ('-total_teencoins',)
