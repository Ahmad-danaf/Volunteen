from django.shortcuts import render
from managementApp.utils.DonationCalculator import DonationCalculator
from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils
from django.utils import timezone
from datetime import datetime, timedelta
import json
from calendar import monthrange
from managementApp.decorators import donation_manager_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from managementApp.models import DonationTransaction, DonationCategory, DonationSpending
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404
from django.http import Http404
from shopApp.models import Shop
from shopApp.utils.shop_manager import ShopManager
from shopApp.utils.ShopDonationUtils import ShopDonationUtils

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

@donation_manager_required
def add_spending(request):
    categories = DonationCategory.objects.filter(is_active=True)
    error_message = None
    success_message = None

    # Get leftovers for each category using the utility method
    leftovers = DonationSpendingUtils.get_leftover_by_category()
    leftovers_dict = {item['category'].id: item['leftover'] for item in leftovers}

    # Attach leftover to each category object
    for cat in categories:
        cat.leftover = leftovers_dict.get(cat.id, 0)

    # Set default category: use the first active category if exists
    default_category_id = categories[0].id if categories else None
    default_leftover = categories[0].leftover if categories else 0
    
    # Get all shops and calculate remaining points for each shop using ShopManager
    shops = Shop.objects.all()  
    for shop in shops:
        shop.remaining_points = ShopManager.get_remaining_points_this_month(shop)

    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            shop_id = request.POST.get('shop')
            amount = int(request.POST.get('amount', 0))
            note = request.POST.get('note', '')

            if amount <= 0:
                raise ValueError("הסכום חייב להיות גדול מאפס.")

            # Get active category or return 404 if not found
            category = get_object_or_404(DonationCategory, id=category_id, is_active=True)
            shop = get_object_or_404(Shop, id=shop_id) if shop_id else None
            if shop is None:
                raise ValueError("חנות לא נבחרה.")

            # Create the spending using the utility class
            DonationSpendingUtils.spend_from_category(category, amount, note, shop)
            success_message = "ההוצאה נרשמה בהצלחה!"

        except ValueError as e:
            error_message = str(e)
        except DonationCategory.DoesNotExist:
            error_message = "הקטגוריה שנבחרה אינה קיימת."
        except Shop.DoesNotExist:
            error_message = "החנות שנבחרה אינה קיימת."
        except Exception as e:
            error_message = f"שגיאה לא צפויה: {str(e)}"

    context = {
        'categories': categories,
        'default_category_id': default_category_id,
        'default_leftover': default_leftover,
        'error_message': error_message,
        'success_message': success_message,
        'category_leftovers': leftovers,  
        'shops': shops,
    }
    return render(request, 'donation/add_spending.html', context)

@donation_manager_required
def recent_donations(request):
    # Get the 20 most recent donations
    donations = DonationTransaction.objects.all().order_by('-date_donated')[:20]
    
    context = {
        'donations': donations,
    }
    return render(request, 'donation/recent_donations.html', context)

@donation_manager_required
def download_report(request):
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
        if end_date_str:
            # Set end date to end of the day
            end_date = timezone.make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
            end_date = end_date.replace(hour=23, minute=59, second=59)
        
        # Generate the CSV report using the utility class
        csv_data = DonationCalculator.export_donations_report(start_date, end_date)
        
        # Return as a downloadable file
        filename = f"donation_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(csv_data)
        return response
    
    # Default to showing the form
    context = {
        'today_date': timezone.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'donation/download_report.html', context)

@donation_manager_required
def top_donors(request):
    # Get top donors by summing total donations per child
    top_donors = DonationTransaction.objects.values(
        'child__user__username', 'child__id'
    ).annotate(
        total_donated=Sum('amount'),
        donation_count=Count('id')
    ).order_by('-total_donated')[:20]
    
    context = {
        'top_donors': top_donors,
    }
    return render(request, 'donation/top_donors.html', context)

@donation_manager_required
def recent_spendings(request):
    """
    Display the 15 most recent spending records.
    Each spending card should include basic details and a link to view the full details.
    Also include a button to view all spendings.
    """
    spendings = DonationSpendingUtils.get_recent_spendings(limit=15)
    
    context = {
        'spendings': spendings,
    }
    return render(request, 'donation/recent_spendings.html', context)


@donation_manager_required
def spending_detail(request, spending_id):
    """
    Display detailed information for a given spending record.
    This includes the spending's note, date, and a list of donation allocations
    (child username, donation amount, amount used, donation date, and donation note).
    """
    details = DonationSpendingUtils.get_spending_details(spending_id)
    if details is None:
        raise Http404("Spending record not found.")
    
    context = {
        'details': details,
    }
    return render(request, 'donation/spending_detail.html', context)


@donation_manager_required
def all_spendings(request):
    spendings = DonationSpending.objects.all().order_by('-date_spent')
    # Extract distinct category names from spendings
    categories = DonationSpending.objects.values_list('category__name', flat=True).distinct()
    context = {
        'spendings': spendings,
        'categories': categories,
    }
    return render(request, 'donation/all_spendings.html', context)


@donation_manager_required
def category_donors(request, category_id):
    """
    View to display all donors who have contributed to a specific category.
    Shows donors sorted by donation amount in descending order.
    """
    try:
        # Get the category
        category = DonationCategory.objects.get(id=category_id)
        
        # Get all donations for this category
        donations = DonationTransaction.objects.filter(
            category=category
        ).order_by('-date_donated')
        
        # Get the total donated to this category
        total_donated = DonationCalculator.get_total_donated(category)
        
        # Get donor statistics (grouped by donor)
        donor_stats = DonationTransaction.objects.filter(
            category=category
        ).values(
            'child__user__username',
            'child__id'
        ).annotate(
            donor_total=Sum('amount'),
            donation_count=Count('id')
        ).order_by('-donor_total')
        
        context = {
            'category': category,
            'donations': donations,
            'total_donated': total_donated,
            'donor_stats': donor_stats,
        }
        return render(request, 'donation/category_donors.html', context)
        
    except DonationCategory.DoesNotExist:
        messages.error(request, "הקטגוריה המבוקשת אינה קיימת")
        return redirect('managementApp:donation_summary_by_category')


@donation_manager_required
def shop_summary(request):
    """
    Display all shops, their remaining points, and total donation spending.
    """
    shops = Shop.objects.all()
    # Attach remaining points + total spent
    for shop in shops:
        shop.remaining_points = ShopManager.get_remaining_points_this_month(shop)
        shop.total_spent = ShopDonationUtils.get_total_donation_spending_for_shop(shop)

    context = {
        'shops': shops,
    }
    return render(request, 'donation/shop_summary.html', context)


@donation_manager_required
def download_shop_report(request):
    msg='download shop report'
    return render(request, 'feature_not_completed.html', {'message': msg})

@donation_manager_required
def shop_detail(request, shop_id):
    shop = get_object_or_404(Shop, id=shop_id)
    
    remaining_points = ShopManager.get_remaining_points_this_month(shop)
    total_spent = ShopDonationUtils.get_total_donation_spending_for_shop(shop)
    spending_by_category = ShopDonationUtils.get_donation_spending_by_category(shop)
    monthly_spent = ShopDonationUtils.get_monthly_donation_spending_for_shop(shop)
    all_spendings = ShopDonationUtils.get_all_spendings_for_shop(shop)
    
    context = {
        'shop': shop,
        'remaining_points': remaining_points,
        'total_spent': total_spent,
        'spending_by_category': spending_by_category,
        'monthly_spent': monthly_spent,
        'all_spendings': all_spendings,
    }
    return render(request, 'donation/shop_detail.html', context)


#####VIEWS FOR campian manager(gonna seprate to other file later)##########