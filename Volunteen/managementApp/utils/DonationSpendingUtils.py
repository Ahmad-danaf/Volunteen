from django.db.models import Sum
from managementApp.models import (
    DonationCategory,
    DonationTransaction,
    DonationSpending,
    SpendingAllocation,
)
from django.db import transaction
from shopApp.models import Shop
from shopApp.utils.shop_manager import ShopManager
from django.utils import timezone
from collections import OrderedDict, deque
class DonationSpendingUtils:
    @staticmethod
    @transaction.atomic
    def spend_from_category(category: DonationCategory, amount: int, note: str = "", shop: Shop = None) -> DonationSpending:
        """
        Creates a new DonationSpending record for the given category and amount,
        then allocates that amount from the oldest unspent DonationTransactions (FIFO).

        Raises a ValueError if there are not enough donations to cover 'amount'.
        """
        if amount <= 0:
            raise ValueError("Spending amount must be positive.")

        # Check leftover to avoid wasting time if insufficient coins
        leftover = DonationSpendingUtils.get_category_leftover(category)
        if leftover < amount:
            raise ValueError(
                f"Not enough donations in category '{category.name}'. "
                f"Requested spending: {amount}, available: {leftover}."
            )
        if shop:
            if ShopManager.get_remaining_points_this_month(shop) < amount:
                raise ValueError(f"Shop '{shop.name}' doesn't have enough points.")
    

        # Create a DonationSpending record
        spending = DonationSpending.objects.create(
            category=category,
            shop=shop,
            amount_spent=amount,
            note=note
        )

        # Distribute the spending in FIFO order among DonationTransaction records
        leftover_to_spend = amount
        transactions = DonationTransaction.objects.filter(category=category).order_by('date_donated')

        for tx in transactions:
            used_already = SpendingAllocation.objects.filter(transaction=tx).aggregate(
                total_used=Sum('amount_used')
            )['total_used'] or 0
            tx_leftover = tx.amount - used_already
            
            if tx_leftover <= 0:
                continue

            allocation_amount = min(leftover_to_spend, tx_leftover)
            if allocation_amount > 0:
                SpendingAllocation.objects.create(
                    spending=spending,
                    transaction=tx,
                    amount_used=allocation_amount
                )
                leftover_to_spend -= allocation_amount

            if leftover_to_spend == 0:
                break

        return spending


    @staticmethod
    @transaction.atomic
    def spend_from_category_fair(
        category: DonationCategory,
        amount: int,
        note: str = "",
        shop: Shop | None = None,
    ) -> DonationSpending:
        """
        Round-robin (child-fair) allocation:
        Each child is selected once before any child is selected again.
        Preserves FIFO order *within* a child's own transactions.
        """
        if amount <= 0:
            raise ValueError("Spending amount must be positive.")

        leftover_category = DonationSpendingUtils.get_category_leftover(category)
        if leftover_category < amount:
            raise ValueError(
                f"Not enough donations in category '{category.name}'. "
                f"Requested: {amount}, available: {leftover_category}."
            )

        if shop and ShopManager.get_remaining_points_this_month(shop) < amount:
            raise ValueError(f"Shop '{shop.name}' doesn't have enough points.")

        spending = DonationSpending.objects.create(
            category=category,
            shop=shop,
            amount_spent=amount,
            note=note,
        )

        # Build child->transactions queue
        transactions = (
            DonationTransaction.objects
            .filter(category=category)
            .order_by("date_donated")          # global chronological order
            .select_related("child")           # avoid extra queries
        )

        # OrderedDict preserves first-seen chronological order of children.
        queue: "OrderedDict[int, deque[DonationTransaction]]" = OrderedDict()
        for tx in transactions:
            queue.setdefault(tx.child_id, deque()).append(tx)

        leftover_to_spend = amount

        # Round-robin allocation loop
        while leftover_to_spend > 0 and queue:
            child_id, child_deque = queue.popitem(last=False)  

            # pull the child's first remaining transaction
            tx = child_deque[0]

            # how much is still unused in this transaction?
            used_already = (
                SpendingAllocation.objects
                .filter(transaction=tx)
                .aggregate(total_used=Sum("amount_used"))
            )["total_used"] or 0
            tx_leftover = tx.amount - used_already
            if tx_leftover <= 0:
                # transaction exhausted – drop it and continue
                child_deque.popleft()
                if child_deque:
                    # child still has more transactions ➜ append to right
                    queue[child_id] = child_deque
                continue

            allocation_amount = min(leftover_to_spend, tx_leftover)

            SpendingAllocation.objects.create(
                spending=spending,
                transaction=tx,
                amount_used=allocation_amount,
            )

            leftover_to_spend -= allocation_amount

            # If transaction is now exhausted, pop it from child's deque
            if allocation_amount == tx_leftover:
                child_deque.popleft()

            # If child still has something left, push them to the back
            if child_deque:
                queue[child_id] = child_deque

        # Defensive check – should always be zero here
        if leftover_to_spend:
            raise RuntimeError(
                "Round-robin allocator ended with leftover_to_spend > 0 "
                "even though pre-validation said enough funds exist."
            )

        return spending

    @staticmethod
    def get_category_leftover(category: DonationCategory) -> int:
        """
        Returns how many TeenCoins are left in the given category 
        (sum of all donations minus sum of all allocated spendings).
        """
        total_donated = DonationTransaction.objects.filter(category=category)\
            .aggregate(sum_amount=Sum('amount'))['sum_amount'] or 0

        total_spent = SpendingAllocation.objects.filter(transaction__category=category)\
            .aggregate(sum_used=Sum('amount_used'))['sum_used'] or 0

        return total_donated - total_spent
    
    
    @staticmethod
    def get_recent_spendings(limit=10):
        """
        Returns the most recent DonationSpending records, ordered by date_spent descending.
        """
        return DonationSpending.objects.all().order_by('-date_spent')[:limit]

    @staticmethod
    def get_spending_details(spending_id):
        """
        Returns a detailed dictionary for a given DonationSpending record, including:
        - Spending details: category name, total amount spent, date, note, and shop info.
        - A list of allocations showing:
            * Donation transaction ID,
            * Donor username,
            * Donation amount,
            * Amount used from that transaction,
            * Donation date and note.
        Returns None if the spending record does not exist.
        """
        try:
            spending = DonationSpending.objects.get(id=spending_id)
        except DonationSpending.DoesNotExist:
            return None

        allocations_qs = SpendingAllocation.objects.filter(spending=spending)\
            .select_related('transaction__child')
        allocations = []
        for alloc in allocations_qs:
            allocations.append({
                'donation_transaction_id': alloc.transaction.id,
                'child_username': alloc.transaction.child.user.username,
                'donation_amount': alloc.transaction.amount,
                'amount_used': alloc.amount_used,
                'donation_date': alloc.transaction.date_donated,
                'donation_note': alloc.transaction.note,
            })

        details = {
            'spending_id': spending.id,
            'category': spending.category.name,
            'amount_spent': spending.amount_spent,
            'date_spent': spending.date_spent,
            'note': spending.note,
            'allocations': allocations,
        }
        if spending.shop:
            details['shop'] = {
                'name': spending.shop.name,
                'img': spending.shop.img.url if spending.shop.img else None,
            }
        else:
            details['shop'] = None

        return details

    @staticmethod
    def get_total_leftover_all_categories() -> int:
        """
        Returns the total leftover TeenCoins across all categories.
        Calculated as (sum of all donations) minus (sum of all allocated coins).
        """
        total_donated = DonationTransaction.objects.aggregate(total=Sum('amount'))['total'] or 0
        total_allocated = SpendingAllocation.objects.aggregate(total=Sum('amount_used'))['total'] or 0
        return total_donated - total_allocated

    @staticmethod
    def get_leftover_by_category():
        """
        Returns a list of dictionaries for each active donation category.
        Each dictionary contains:
            - 'category': the DonationCategory instance,
            - 'leftover': remaining TeenCoins (donated - allocated).
        """
        results = []
        categories = DonationCategory.objects.filter(is_active=True)
        for cat in categories:
            leftover = DonationSpendingUtils.get_category_leftover(cat)
            results.append({
                'category': cat,
                'leftover': leftover
            })
        return results