from django.shortcuts import render
from managementApp.utils.DonationCalculator import DonationCalculator
from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils
from django.utils import timezone
from datetime import datetime, timedelta
import json
from calendar import monthrange
from managementApp.decorators import donation_manager_required

@donation_manager_required
def donation_manager_dashboard(request):
    current_year = timezone.now().year
    # Overall stats
    total_donated = DonationCalculator.get_total_donated()
    total_spent = DonationCalculator.get_total_spent()
    balance = DonationSpendingUtils.get_total_leftover_all_categories()
    
    # Build monthly donations and spendings for the current year
    monthly_donations = []
    monthly_spendings = []
    for month in range(1, 13):
        start_date = timezone.make_aware(datetime(current_year, month, 1))
        end_date = timezone.make_aware(datetime(
            current_year, month, monthrange(current_year, month)[1], 23, 59, 59))
        donation_total = DonationCalculator.get_total_donated(None, start_date, end_date)
        spending_total = DonationCalculator.get_total_spent(None, start_date, end_date)
        monthly_donations.append(donation_total)
        monthly_spendings.append(spending_total)
    
    context = {
        'total_donated': total_donated,
        'total_spent': total_spent,
        'balance': balance,
        # Pass JSON strings to be parsed in JavaScript
        'monthly_donations': json.dumps(monthly_donations),
        'monthly_spendings': json.dumps(monthly_spendings),
        'current_date': timezone.now().strftime('%A, %d %B %Y'),
    }
    
    return render(request, 'donation/donation_dashboard.html', context)

@donation_manager_required
def donation_summary_by_category(request):
    category_summaries = DonationCalculator.get_category_summary()
    
    context = {
        'category_summaries': category_summaries,
    }
    return render(request, 'donation/donation_summary_by_category.html', context)


