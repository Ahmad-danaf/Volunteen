from django.contrib import admin
from .models import DonationCategory, DonationTransaction, DonationSpending, SpendingAllocation

class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'last_selected_child')
    search_fields = ('name',)
    
    def last_selected_child_display(self, obj):
        if obj.last_selected_child:
            return obj.last_selected_child.user.username
        return "-"
    last_selected_child_display.short_description = "Last Picked Child"
    

class DonationTransactionAdmin(admin.ModelAdmin):
    list_display = ('child', 'category', 'amount', 'date_donated')
    list_filter = ('category', 'date_donated')
    search_fields = ('child__name', 'category__name')
    
    
class DonationSpendingAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount_spent', 'date_spent')
    list_filter = ('category', 'date_spent')
    search_fields = ('category__name',)
    
class SpendingAllocationAdmin(admin.ModelAdmin):
    list_display = ('spending', 'transaction', 'amount_used')
    list_filter = ('spending__category', 'transaction__child')
    search_fields = ('spending__category__name', 'transaction__child__name')
    
admin.site.register(DonationCategory, DonationCategoryAdmin)
admin.site.register(DonationTransaction, DonationTransactionAdmin)
admin.site.register(DonationSpending, DonationSpendingAdmin)
admin.site.register(SpendingAllocation, SpendingAllocationAdmin)

