from django.db.models import Sum
from django.utils import timezone
from managementApp.models import DonationTransaction, DonationSpending, DonationCategory
from calendar import monthrange


class DonationCalculator:
    """
    Utility class that provides static methods to calculate donated, spent,
    and leftover amounts for a given category or date range.
    """

    @staticmethod
    def get_total_donated(category=None, start_date=None, end_date=None):
        """
        Returns the total donated amount for a specific category (if provided).
        Optionally filters by a date range using start_date and end_date.
        If no category is provided, returns the total donated across all categories.
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
        Returns the total spent amount for a specific category (if provided).
        Optionally filters by a date range using start_date and end_date.
        If no category is provided, returns the total spent across all categories.
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
    def get_leftover(category=None, start_date=None, end_date=None):
        """
        Returns the leftover (donated - spent) for a specific category (if provided).
        Optionally filters by the same date range for donated and spent data.
        If no category is provided, returns the leftover across all categories.
        """
        total_donated = DonationCalculator.get_total_donated(category, start_date, end_date)
        total_spent = DonationCalculator.get_total_spent(category, start_date, end_date)
        return total_donated - total_spent

    @staticmethod
    def get_monthly_summary(year, month):
        """
        Returns a list of categories with donated, spent, and leftover for a specific month.
        Useful for monthly reporting. 
        """
        start_date = timezone.datetime(year, month, 1)
        # end_date should be the last day of the month; monthrange(year, month) returns (weekday, days_in_month)
        end_date = timezone.datetime(year, month, monthrange(year, month)[1], 23, 59, 59)

        categories = DonationCategory.objects.all()
        summary = []

        for cat in categories:
            donated = DonationCalculator.get_total_donated(cat, start_date, end_date)
            spent = DonationCalculator.get_total_spent(cat, start_date, end_date)
            leftover = donated - spent
            summary.append({
                'category': cat,
                'donated': donated,
                'spent': spent,
                'leftover': leftover,
            })

        return summary