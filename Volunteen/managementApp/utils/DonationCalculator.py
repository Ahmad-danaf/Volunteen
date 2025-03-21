from django.db.models import Sum
from django.utils import timezone
from calendar import monthrange
from managementApp.models import DonationTransaction, DonationSpending, DonationCategory

class DonationCalculator:
    """
    Utility class that provides static methods to calculate donation totals,
    summaries, and to export reports over a given date range.
    """

    @staticmethod
    def get_total_donated(category=None, start_date=None, end_date=None):
        """
        Returns the total donated amount for a specific category (if provided),
        optionally filtered by a date range. If no category is provided, returns
        the total donated across all categories.
        """
        qs = DonationTransaction.objects.all()
        if category:
            qs = qs.filter(category=category)
        if start_date:
            qs = qs.filter(date_donated__gte=start_date)
        if end_date:
            qs = qs.filter(date_donated__lte=end_date)
        result = qs.aggregate(total_donated=Sum('amount'))['total_donated']
        return result if result else 0

    @staticmethod
    def get_total_spent(category=None, start_date=None, end_date=None):
        """
        Returns the total spent amount for a specific category (if provided),
        optionally filtered by a date range. If no category is provided, returns
        the total spent across all categories.
        """
        qs = DonationSpending.objects.all()
        if category:
            qs = qs.filter(category=category)
        if start_date:
            qs = qs.filter(date_spent__gte=start_date)
        if end_date:
            qs = qs.filter(date_spent__lte=end_date)
        result = qs.aggregate(total_spent=Sum('amount_spent'))['total_spent']
        return result if result else 0

    @staticmethod
    def get_category_summary(start_date=None, end_date=None):
        """
        Returns a summary for each active donation category.
        For each category, includes:
         - total donated
         - total spent
         - leftover (donated - spent)
        Optionally filters all figures by a date range.
        """
        summaries = []
        categories = DonationCategory.objects.filter(is_active=True)
        for category in categories:
            total_donated = DonationCalculator.get_total_donated(category, start_date, end_date)
            total_spent = DonationCalculator.get_total_spent(category, start_date, end_date)
            leftover = total_donated - total_spent
            summaries.append({
                'category': category,
                'total_donated': total_donated,
                'total_spent': total_spent,
                'leftover': leftover,
            })
        return summaries

    @staticmethod
    def get_monthly_donations_by_category(year):
        """
        Returns a dictionary mapping each active category's ID to its monthly donation totals
        for the given year. For each category, the value is a dictionary with:
            - 'category': the category instance
            - 'monthly_totals': a list of 12 integers (one per month, January to December)
        """
        monthly_data = {}
        categories = DonationCategory.objects.filter(is_active=True)
        for category in categories:
            monthly_totals = []
            for month in range(1, 13):
                start_date = timezone.datetime(year, month, 1)
                end_day = monthrange(year, month)[1]
                end_date = timezone.datetime(year, month, end_day, 23, 59, 59)
                # Make dates timezone-aware if they aren't already
                if timezone.is_naive(start_date):
                    start_date = timezone.make_aware(start_date)
                if timezone.is_naive(end_date):
                    end_date = timezone.make_aware(end_date)
                total = DonationCalculator.get_total_donated(category, start_date, end_date)
                monthly_totals.append(total)
            monthly_data[category.id] = {
                'category': category,
                'monthly_totals': monthly_totals
            }
        return monthly_data

    @staticmethod
    def export_donations_report(start_date=None, end_date=None):
        """
        Exports a CSV report of donation transactions filtered by an optional date range.
        The report includes:
            Donation ID, Child Username, Category, Amount, Date Donated, and Note.
        Returns the CSV data as a string.
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Donation ID", "Child Username", "Category", "Amount", "Date Donated", "Note"])
        
        qs = DonationTransaction.objects.all().order_by('date_donated')
        if start_date:
            qs = qs.filter(date_donated__gte=start_date)
        if end_date:
            qs = qs.filter(date_donated__lte=end_date)
        
        for donation in qs:
            writer.writerow([
                donation.id,
                donation.child.user.username,
                donation.category.name,
                donation.amount,
                donation.date_donated.strftime("%Y-%m-%d %H:%M:%S"),
                donation.note or ""
            ])
        return output.getvalue()
