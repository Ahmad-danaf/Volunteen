from django.contrib import admin
from .models import DonationCategory, DonationTransaction

class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

class DonationTransactionAdmin(admin.ModelAdmin):
    list_display = ('child', 'category', 'amount', 'date_donated')
    list_filter = ('category', 'date_donated')
    search_fields = ('child__name', 'category__name')

admin.site.register(DonationCategory, DonationCategoryAdmin)
admin.site.register(DonationTransaction, DonationTransactionAdmin)

