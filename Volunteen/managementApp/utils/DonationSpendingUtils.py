from django.db.models import Sum
from managementApp.models import (
    DonationCategory,
    DonationTransaction,
    DonationSpending,
    SpendingAllocation,
)
from django.db import transaction
from django_q.tasks import async_task
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
        shop=None,
    ) -> DonationSpending:
        """
        Persistent round-robin (child-fair) allocator that:
        - Remembers the last child picked in previous spendings.
        - Ensures each child is picked only once per cycle inside a single spending.
        - Resets cycle only after all active children had a turn.
        """

        # Lock category row to prevent concurrent spends corrupting the pointer
        category = DonationCategory.objects.select_for_update().get(pk=category.pk)

        # Validations
        if amount <= 0:
            raise ValueError("Spending amount must be positive.")

        leftover = DonationSpendingUtils.get_category_leftover(category)
        if leftover < amount:
            raise ValueError(f"Not enough donations in category '{category.name}'. Requested: {amount}, available: {leftover}.")

        if shop and ShopManager.get_remaining_points_this_month(shop) < amount:
            raise ValueError(f"Shop '{shop.name}' doesn't have enough points.")

        # Create the spending record
        spending = DonationSpending.objects.create(
            category=category,
            shop=shop,
            amount_spent=amount,
            note=note,
        )

        # Build child → transaction queue
        transactions = (
            DonationTransaction.objects
            .filter(category=category)
            .order_by("date_donated")
            .select_related("child")
        )

        queue: OrderedDict[int, deque] = OrderedDict()
        for tx in transactions:
            queue.setdefault(tx.child_id, deque()).append(tx)

        # Rotate queue based on last selected child
        last_pointer = category.last_selected_child_id
        if last_pointer in queue:
            while next(iter(queue)) != last_pointer:
                k, v = queue.popitem(last=False)
                queue[k] = v
            # move the pointer child itself to end
            k, v = queue.popitem(last=False)
            queue[k] = v

        # Allocation logic
        leftover_to_spend = amount
        selected_this_cycle = set()
        initial_cycle_size = len(queue)
        last_child_used = None

        while leftover_to_spend > 0 and queue:
            child_id, child_tx_queue = queue.popitem(last=False)

            if not child_tx_queue:
                continue

            tx = child_tx_queue[0]
            used = (
                SpendingAllocation.objects
                .filter(transaction=tx)
                .aggregate(total_used=Sum('amount_used'))
            )['total_used'] or 0

            tx_leftover = tx.amount - used
            if tx_leftover <= 0:
                child_tx_queue.popleft()
                if child_tx_queue:
                    queue[child_id] = child_tx_queue
                continue

            allocation_amount = min(leftover_to_spend, tx_leftover)

            SpendingAllocation.objects.create(
                spending=spending,
                transaction=tx,
                amount_used=allocation_amount
            )

            leftover_to_spend -= allocation_amount
            last_child_used = child_id

            if allocation_amount == tx_leftover:
                child_tx_queue.popleft()

            if child_tx_queue:
                selected_this_cycle.add(child_id)
                if len(selected_this_cycle) == initial_cycle_size:
                    selected_this_cycle.clear()
                queue[child_id] = child_tx_queue

        if leftover_to_spend > 0:
            raise RuntimeError("Spending ended with leftover amount, despite passing validation.")

        # Save pointer for next time
        category.last_selected_child_id = last_child_used
        category.save(update_fields=["last_selected_child"])
        
        selected_child_ids = (
            SpendingAllocation.objects
            .filter(spending=spending)
            .values_list("transaction__child_id", flat=True)
            .distinct()
        )
        try:
            transaction.on_commit(lambda: async_task(
                "managementApp.tasks.donation_thx_notifications.send_donation_thank_you_messages",
                list(selected_child_ids),
                spending.id,
                q_options={
                    "timeout": 900,
                    "max_attempts": 1,
                    "group": f"donation_thx_{spending.id}",
                    "ack_failures": True,
                }
            ))
        except Exception as e:
            print(f"Failed to queue thank-you notification task: {e}")

        return spending
    
    @staticmethod
    def simulate_spend_from_category_fair(category: DonationCategory, amount: int):
        """
        Simulate a persistent fair spend:
        - Returns a list of child allocations WITHOUT saving anything.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive.")

        leftover = DonationSpendingUtils.get_category_leftover(category)
        if leftover < amount:
            raise ValueError("Not enough coins.")

        transactions = (
            DonationTransaction.objects
            .filter(category=category)
            .order_by("date_donated")
            .select_related("child", "child__user")
        )

        queue: OrderedDict[int, deque] = OrderedDict()
        for tx in transactions:
            queue.setdefault(tx.child_id, deque()).append(tx)

        last_pointer = category.last_selected_child_id
        if last_pointer in queue:
            while next(iter(queue)) != last_pointer:
                k, v = queue.popitem(last=False)
                queue[k] = v
            k, v = queue.popitem(last=False)
            queue[k] = v

        leftover_to_spend = amount
        selected_this_cycle = set()
        initial_cycle_size = len(queue)
        result = []
        child_alloc_map = {}  # {child_id: {'child':..., 'amount':..., 'tx_ids': [...]}}

        while leftover_to_spend > 0 and queue:
            child_id, child_tx_queue = queue.popitem(last=False)
            child = child_tx_queue[0].child

            if not child_tx_queue:
                continue

            tx = child_tx_queue[0]
            used = (
                SpendingAllocation.objects
                .filter(transaction=tx)
                .aggregate(total_used=Sum("amount_used"))
            )["total_used"] or 0
            tx_left = tx.amount - used
            if tx_left <= 0:
                child_tx_queue.popleft()
                if child_tx_queue:
                    queue[child_id] = child_tx_queue
                continue

            alloc = min(leftover_to_spend, tx_left)
            leftover_to_spend -= alloc

            if child_id not in child_alloc_map:
                child_alloc_map[child_id] = {
                    "child": child.user.username,
                    "child_id": child.id,
                    "allocated": 0,
                    "from_transactions": []
                }
            child_alloc_map[child_id]["allocated"] += alloc
            child_alloc_map[child_id]["from_transactions"].append(tx.id)

            if alloc == tx_left:
                child_tx_queue.popleft()
            if child_tx_queue:
                selected_this_cycle.add(child_id)
                if len(selected_this_cycle) == initial_cycle_size:
                    selected_this_cycle.clear()
                queue[child_id] = child_tx_queue

        return list(child_alloc_map.values())

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
    def get_spending_details_grouped_by_child(spending_id):
        """
        Returns grouped details of a spending, per child:
        - Total used per child
        - All donation notes and amounts used
        """
        try:
            spending = DonationSpending.objects.get(id=spending_id)
        except DonationSpending.DoesNotExist:
            return None

        allocations = (
            SpendingAllocation.objects
            .filter(spending=spending)
            .select_related('transaction__child__user')
        )

        child_map = {}  # child_id → entry
        for alloc in allocations:
            child = alloc.transaction.child
            child_id = child.id
            tx = alloc.transaction

            if child_id not in child_map:
                child_map[child_id] = {
                    "child_id": child_id,
                    "username": child.user.username,
                    "total_used": 0,
                    "transactions": []
                }

            child_map[child_id]["total_used"] += alloc.amount_used
            child_map[child_id]["transactions"].append({
                "transaction_id": tx.id,
                "donation_amount": tx.amount,
                "amount_used": alloc.amount_used,
                "date": tx.date_donated,
                "note": tx.note,
            })

        details = {
            "spending_id": spending.id,
            "category": spending.category.name,
            "amount_spent": spending.amount_spent,
            "date_spent": spending.date_spent,
            "note": spending.note,
            "children": list(child_map.values()),
        }

        if spending.shop:
            details["shop"] = {
                "name": spending.shop.name,
                "img": spending.shop.img.url if spending.shop.img else None,
            }
        else:
            details["shop"] = None

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
        categories = DonationCategory.objects.all()
        for cat in categories:
            leftover = DonationSpendingUtils.get_category_leftover(cat)
            results.append({
                'category': cat,
                'leftover': leftover
            })
        return results