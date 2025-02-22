from datetime import datetime, timedelta
from django.db.models import Count, Q
from shopApp.models import Redemption, Shop

def purchase_all_businesses(child):
    all_businesses = set(Shop.objects.values_list('id', flat=True))
    businesses_purchased = set(
        Redemption.objects.filter(child=child).values_list('shop__id', flat=True)
    )
    return all_businesses == businesses_purchased