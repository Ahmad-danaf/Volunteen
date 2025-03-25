from django.db.models import Sum
from django.utils import timezone
from shopApp.models import Shop
from managementApp.models import DonationSpending

class ShopDonationUtils:
    """
    Utility methods for handling donation spending statistics for shops.
    """

    @staticmethod
    def get_monthly_donation_spending_for_shop(shop: Shop) -> int:
        """
        Returns the total amount of TeenCoins spent at the given shop in the current month.
        """
        if not shop:
            raise ValueError("חנות לא נבחרה.")
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = DonationSpending.objects.filter(
            shop=shop,
            date_spent__gte=start_of_month
        ).aggregate(total_spent=Sum('amount_spent'))['total_spent'] or 0
        return result

    @staticmethod
    def get_total_donation_spending_for_shop(shop: Shop) -> int:
        """
        Returns the total donation spending for the given shop (all time).
        """
        if not shop:
            raise ValueError("חנות לא נבחרה.")
        result = DonationSpending.objects.filter(shop=shop).aggregate(total_spent=Sum('amount_spent'))['total_spent'] or 0
        return result

    @staticmethod
    def get_donation_spending_by_category(shop: Shop) -> dict:
        """
        Returns a dictionary mapping each category name to the total donation spending 
        for that category at the given shop.
        Example return: { "מזון": 1500, "ביגוד": 750 }
        """
        if not shop:
            raise ValueError("חנות לא נבחרה.")
        qs = DonationSpending.objects.filter(shop=shop)
        data = qs.values('category__name').annotate(total_spent=Sum('amount_spent'))
        return { item['category__name']: item['total_spent'] for item in data }

    @staticmethod
    def get_donation_spending_in_date_range(shop: Shop, start_date, end_date) -> int:
        """
        Returns the total donation spending for the given shop between start_date and end_date.
        """
        if not shop:
            raise ValueError("חנות לא נבחרה.")
        result = DonationSpending.objects.filter(
            shop=shop,
            date_spent__gte=start_date,
            date_spent__lte=end_date
        ).aggregate(total_spent=Sum('amount_spent'))['total_spent'] or 0
        return result

    @staticmethod
    def get_all_spendings_for_shop(shop: Shop,limit=None) -> list:
        """
        Returns a list of all donation spending records for the given shop.
        Each record is represented as a dictionary with:
         - date_spent
         - note (if any)
         - amount_spent
         - category (name)
        """
        if not shop:
            raise ValueError("חנות לא נבחרה.")
        qs = DonationSpending.objects.filter(shop=shop).order_by('-date_spent')
        spendings = []
        if limit is not None:
            qs = qs[:limit]
        for spending in qs:
            spendings.append({
                'date_spent': spending.date_spent,
                'note': spending.note,
                'amount_spent': spending.amount_spent,
                'category': spending.category.name,
            })
        return spendings