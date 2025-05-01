from collections import Counter
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch

from childApp.models import Child
from django.contrib.auth.models import User
from managementApp.models import (
    DonationCategory,
    DonationTransaction,
    SpendingAllocation,
)
from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils
from shopApp.models import Shop
from django.db.models import Sum
# ----------------------------------------------------------------------
# Helper
# ----------------------------------------------------------------------
def _make_child_with_identifier(username: str, identifier: str = None) -> Child:
    u = User.objects.create(username=username)
    if identifier is None:
        identifier = username[:5]
    while Child.objects.filter(identifier=identifier).exists():
        identifier = str(int(identifier) + 1)
    
    return Child.objects.create(
        user=u,
        identifier=identifier,
        secret_code=username[:3],
    )

# ------------------------------------------------------------------
#  helper: resets numeric identifier seed each TestCase
# ------------------------------------------------------------------
def _make_child(username: str) -> Child:
    # next free five-digit identifier
    base = 0
    while True:
        ident = f"{base:05d}"
        if not Child.objects.filter(identifier=ident).exists():
            break
        base += 1

    user = User.objects.create(username=username)
    return Child.objects.create(
        user=user,
        identifier=ident,
        secret_code=username[:3],
    )
class DonationSpendingRoundRobinTests(TestCase):
    """
    Independent tests that target the *persistent* round-robin allocator
    (DonationSpendingUtils.spend_from_category_fair).
    """

    def setUp(self):
        # One active category for all tests
        self.category = DonationCategory.objects.create(
            name="Education", is_active=True
        )

        # One shop with ample balance
        shop_user = User.objects.create(username="shop_user")
        self.shop = Shop.objects.create(user=shop_user, name="Shop", max_points=10_000)

        # Shortcuts for time ordering
        self.now = timezone.now()
        self.day_ago = self.now - timedelta(days=1)
        self.week_ago = self.now - timedelta(days=7)

    # ------------------------------------------------------------------
    # 1. Six-children rotation across spendings
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_six_children_two_each_spending(self, mock_points):
        """
        Create 6 children (donations of ₪50 each).
        Spend ₪100 three times.
        Expect first spend → child1 & child2
               second spend → child3 & child4
               third  spend → child5 & child6
        """
        mock_points.return_value = 1_000

        children = []
        for i in range(6):
            c = _make_child_with_identifier(f"child{i+1}", identifier=f"CH00{i+1}")
            children.append(c)
            DonationTransaction.objects.create(
                child=c,
                category=self.category,
                amount=50,
                note=f"first donation {i+1}",
                # ensure chronological order
                date_donated=self.week_ago + timedelta(minutes=i),
            )

        selected_batches = []  # list[list(child_id)]
        for _ in range(3):
            spending = DonationSpendingUtils.spend_from_category_fair(
                category=self.category,
                amount=100,  # requires exactly two donations
                note="batch spending",
                shop=self.shop,
            )
            batch_child_ids = list(
                SpendingAllocation.objects.filter(spending=spending)
                .values_list("transaction__child_id", flat=True)
                .distinct()
            )
            selected_batches.append(batch_child_ids)

        # Convert children list to ids for direct comparison
        child_ids = [c.id for c in children]

        # Expected batches: [child1, child2], [child3, child4], [child5, child6]
        self.assertEqual(
            selected_batches[0],
            child_ids[0:2],
            msg="Batch 1 should select first two children chronologically",
        )
        self.assertEqual(
            selected_batches[1],
            child_ids[2:4],
            msg="Batch 2 should select next two children in queue",
        )
        self.assertEqual(
            selected_batches[2],
            child_ids[4:6],
            msg="Batch 3 should select final two children",
        )

    # ------------------------------------------------------------------
    # 2. New child appears after first spending
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_new_child_priority_after_pointer(self, mock_points):
        """
        After first spending (childA picked last), add childC donation.
        Next spending should start with childB (waiting longest) then childC.
        """
        mock_points.return_value = 1_000

        child_a = _make_child_with_identifier("Alice", identifier="CH009")
        child_b = _make_child_with_identifier("Bob", identifier="CH010")

        DonationTransaction.objects.create(
            child=child_a, category=self.category, amount=50, note="A old", date_donated=self.week_ago
        )
        DonationTransaction.objects.create(
            child=child_b, category=self.category, amount=50, note="B old", date_donated=self.day_ago
        )

        # Spend 50 → picks Alice, pointer now Alice
        DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=50, note="first", shop=self.shop
        )

        # Insert new child C
        child_c = _make_child_with_identifier("Charlie", identifier="CH011")
        DonationTransaction.objects.create(
            child=child_c, category=self.category, amount=50, note="C new", date_donated=self.now
        )

        # Next spend 100 (needs 2 children)
        spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=100, note="second", shop=self.shop
        )
        order = list(
            SpendingAllocation.objects.filter(spending=spending)
            .values_list("transaction__child__user__username", flat=True)
            .distinct()
        )
        self.assertEqual(order[0], "Bob")      # first after pointer
        self.assertEqual(order[1], "Charlie")  # new child included before Alice repeats

    # ------------------------------------------------------------------
    # 3. Partial transaction leftover respected
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_leftover_respected(self, mock_points):
        """
        Donate 50, spend 30, then spend 20 → second spending should reuse same tx.
        """
        mock_points.return_value = 1_000

        child = _make_child_with_identifier("LeftoverKid", identifier="CH012")
        tx = DonationTransaction.objects.create(
            child=child, category=self.category, amount=50
        )

        # first spend 30
        DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=30, note="part1", shop=self.shop
        )
        # second spend 20
        spending2 = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=20, note="part2", shop=self.shop
        )

        allocs = SpendingAllocation.objects.filter(spending=spending2)
        self.assertEqual(allocs.count(), 1)
        self.assertEqual(allocs.first().transaction, tx)
        self.assertEqual(allocs.first().amount_used, 20)

    # ------------------------------------------------------------------
    # 4. Cycle reset inside single large spending
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_no_duplicate_until_all_seen(self, mock_points):
        """
        Two children donate 60 each. Spend 100 in one call.
        Expect allocation order: child1 (60) → child2 (40). No duplicate child1 until child2 seen.
        """
        mock_points.return_value = 1_000

        c1 = _make_child_with_identifier("C1", identifier="CH013")
        c2 = _make_child_with_identifier("C2", identifier="CH014")

        DonationTransaction.objects.bulk_create(
            [
                DonationTransaction(child=c1, category=self.category, amount=60, note="c1"),
                DonationTransaction(child=c2, category=self.category, amount=60, note="c2"),
            ]
        )

        spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=100, note="big spend", shop=self.shop
        )
        order = list(
            SpendingAllocation.objects.filter(spending=spending)
            .values_list("transaction__child__user__username", flat=True)
        )
        # Expect first 60 from c1, then remaining 40 from c2
        self.assertEqual(order[:1], ["C1"])
        self.assertEqual(order[1:], ["C2"])

    # ------------------------------------------------------------------
    # 5. Validation: insufficient funds still rolls back
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_insufficient_funds_rollback(self, mock_points):
        child = _make_child_with_identifier("PoorKid", identifier="CH015")
        DonationTransaction.objects.create(child=child, category=self.category, amount=10)
        mock_points.return_value = 1_000

        with self.assertRaises(ValueError):
            DonationSpendingUtils.spend_from_category_fair(
                category=self.category, amount=99, note="fail", shop=self.shop
            )

        # No spending or allocation rows should exist
        self.assertEqual(SpendingAllocation.objects.count(), 0)

    # ------------------------------------------------------------------
    # 6. FIFO first, then FAIR – verify pointer starts after last FIFO child
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_fifo_then_fair_pointer_carry(self, mock_pts):
        """
        Spend 50 with old FIFO (picks childA).
        Spend 50 with new FAIR (should pick childB first, not childA again).
        """
        mock_pts.return_value = 1_000
        c_a = _make_child("A")
        c_b = _make_child("B")

        DonationTransaction.objects.bulk_create([
            DonationTransaction(child=c_a, category=self.category, amount=50, date_donated=self.week_ago),
            DonationTransaction(child=c_b, category=self.category, amount=50, date_donated=self.day_ago),
        ])

        # FIFO spend → picks childA, pointer still null (FIFO doesn't update it)
        from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils as DSU
        DSU.spend_from_category(
            category=self.category, amount=50, note="fifo", shop=self.shop
        )

        # Now new fair spend; queue rotation should still start with childB
        spend_fair = DSU.spend_from_category_fair(
            category=self.category, amount=50, note="fair", shop=self.shop
        )
        first_child = SpendingAllocation.objects.filter(
            spending=spend_fair
        ).values_list("transaction__child__user__username", flat=True).first()
        self.assertEqual(first_child, "B")

    # ------------------------------------------------------------------
    # 7. FAIR first, then FIFO – FIFO must respect remaining order
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_fair_then_fifo_leftover_order(self, mock_pts):
        """
        Spend 75 with fair (child1→child2). Remaining 25 should be child2.
        FIFO spend 25 must pick child2, not child1.
        """
        from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils as DSU
        mock_pts.return_value = 1_000
        c1 = _make_child("one")
        c2 = _make_child("two")

        DonationTransaction.objects.bulk_create([
            DonationTransaction(child=c1, category=self.category, amount=50, date_donated=self.week_ago),
            DonationTransaction(child=c2, category=self.category, amount=50, date_donated=self.day_ago),
        ])

        DSU.spend_from_category_fair(
            category=self.category, amount=75, note="fair1", shop=self.shop
        )
        fifo_spend = DSU.spend_from_category(
            category=self.category, amount=25, note="fifo2", shop=self.shop
        )
        alloc_child = SpendingAllocation.objects.filter(
            spending=fifo_spend
        ).values_list("transaction__child__user__username", flat=True).first()
        self.assertEqual(alloc_child, "two")

    # ------------------------------------------------------------------
    # 8. Six-child 2×2×2 cycle including pointer persistence
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_six_children_two_each_three_spendings(self, mock_pts):
        """
        6 children donate 40 each. Spend 80 three times.
        Expect batches: (1,2) → (3,4) → (5,6) in that order.
        """
        mock_pts.return_value = 1_000
        donors = [_make_child(f"c{i}") for i in range(1, 7)]
        for idx, child in enumerate(donors):
            DonationTransaction.objects.create(
                child=child, category=self.category, amount=40,
                date_donated=self.week_ago + timedelta(minutes=idx)
            )
        batches = []
        for _ in range(3):
            s = DonationSpendingUtils.spend_from_category_fair(
                category=self.category, amount=80, note="batch", shop=self.shop
            )
            batch = list(
                SpendingAllocation.objects.filter(spending=s)
                .values_list("transaction__child__identifier", flat=True)
                .distinct()
            )
            batches.append(batch)

        expected = [[d.identifier for d in donors[i:i+2]] for i in range(0, 6, 2)]
        self.assertEqual(batches, expected)

    # ------------------------------------------------------------------
    # 9. All children exhausted – new donation from old child appears
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_child_returns_after_exhaustion(self, mock_pts):
        """
        Child X exhausted in earlier spendings. Later makes a new donation.
        Next spending should include X again in rotation.
        """
        mock_pts.return_value = 1_000
        c_x = _make_child("returner")
        c_y = _make_child("stay")

        DonationTransaction.objects.bulk_create([
            DonationTransaction(child=c_x, category=self.category, amount=30),
            DonationTransaction(child=c_y, category=self.category, amount=30),
        ])

        # Spend 60 → both exhausted
        DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=60, note="first", shop=self.shop
        )
        # New donation for c_x
        DonationTransaction.objects.create(child=c_x, category=self.category, amount=20)

        spend_next = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=20, note="second", shop=self.shop
        )
        chosen = SpendingAllocation.objects.filter(
            spending=spend_next
        ).values_list("transaction__child__user__username", flat=True).first()
        self.assertEqual(chosen, "returner")
        
    # ------------------------------------------------------------------
    # 10. Pointer child exhausted is auto-skipped next spending
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_pointer_exhausted_skip(self, mock_pts):
        mock_pts.return_value = 1_000
        c1 = _make_child("ptr1")
        c2 = _make_child("ptr2")
        DonationTransaction.objects.create(child=c1, category=self.category, amount=30)
        DonationTransaction.objects.create(child=c2, category=self.category, amount=30)

        # Spend full 30 from c1  → pointer=c1
        DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=30, note="first", shop=self.shop
        )
        # second spend 30 should pick c2 because c1 is exhausted
        s2 = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=30, note="second", shop=self.shop
        )
        chosen = SpendingAllocation.objects.filter(
            spending=s2).values_list("transaction__child__user__username", flat=True).first()
        self.assertEqual(chosen, "ptr2")

    # ------------------------------------------------------------------
    # 11. 1 000 donations, 100 children, fairness cycles correctly
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_thousand_donations_fair_order(self, mock_pts):
        mock_pts.return_value = 1_000
        # 100 children × 10 donations of 5 each
        for i in range(100):
            child = _make_child(f"bulk{i}")
            for j in range(10):
                DonationTransaction.objects.create(
                    child=child, category=self.category, amount=5,
                    date_donated=self.week_ago + timedelta(minutes=(i*10+j))
                )

        # Spend 500 (should touch exactly first 100 kids once each)
        s = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=500, note="bulk", shop=self.shop
        )
        kids_chosen = list(SpendingAllocation.objects.filter(spending=s)
                        .values_list("transaction__child_id", flat=True)
                        .distinct())

        # Must be 100 distinct children
        self.assertEqual(len(kids_chosen), 100)
        # in chronological id order (because first cycle)
        self.assertEqual(sorted(kids_chosen), kids_chosen)

    # ------------------------------------------------------------------
    # 12. 1 000 donations, 100 children, fairness cycles correctly
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_thousand_donations_fair_order_100_children(self, mock_pts):
        mock_pts.return_value = 1_000
        # 100 children × 10 donations of 5 each
        for i in range(100):
            child = _make_child_with_identifier(f"bulk{i}", identifier=f"CH0{i}")
            for j in range(10):
                DonationTransaction.objects.create(
                    child=child, category=self.category, amount=5,
                    date_donated=self.week_ago + timedelta(minutes=(i*10+j))
                )
        # Spend 500 (should touch exactly first 100 kids once each)
        s = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=500, note="bulk", shop=self.shop
        )
        kids_chosen = list(SpendingAllocation.objects.filter(spending=s)
                        .values_list("transaction__child_id", flat=True)
                        .distinct())
        # Must be 100 distinct children
        self.assertEqual(len(kids_chosen), 100)
        # in chronological id order (because first cycle)
        self.assertEqual(sorted(kids_chosen), kids_chosen)
        
        
    # ------------------------------------------------------------------
    # 13. 1 000 donations, 100 children, fairness cycles correctly
    # ------------------------------------------------------------------
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_thousand_donations_fair_order_5_children(self, mock_pts):
        mock_pts.return_value = 1_000
        # 100 children × 10 donations of 5 each
        for i in range(100):
            child = _make_child_with_identifier(f"bulk{i}", identifier=f"CH0{i}")
            for j in range(10):
                DonationTransaction.objects.create(
                    child=child, category=self.category, amount=1,
                    date_donated=self.week_ago + timedelta(minutes=(i*10+j))
                )
        # Spend 500 (should touch exactly first 100 kids once each)
        s = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=5, note="bulk", shop=self.shop
        )
        kids_chosen = list(SpendingAllocation.objects.filter(spending=s)
                        .values_list("transaction__child_id", flat=True)
                        .distinct())
        # Must be 100 distinct children
        self.assertEqual(len(kids_chosen), 5)
        # in chronological id order (because first cycle)
        self.assertEqual(sorted(kids_chosen), kids_chosen)
        
        s2=DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=5, note="bulk", shop=self.shop
        )
        kids_chosen2 = list(SpendingAllocation.objects.filter(spending=s2)
                        .values_list("transaction__child_id", flat=True)
                        .distinct())
        self.assertEqual(len(kids_chosen2), 5)
        self.assertEqual(sorted(kids_chosen2), kids_chosen2)
        for i in kids_chosen2:
            if i in kids_chosen:
                self.fail(f"child {i} should not be chosen again")  

        

    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_persistent_fair_rotation_over_batches(self, mock_pts):
        """
        100 children × 10 donations = 1 000 total
        Spend 5 coins each round × 20 rounds
        ➜ Must rotate through 100 children in order,
        ➜ Each child appears once before repeat
        ➜ No child appears twice until cycle restarts
        """
        mock_pts.return_value = 10_000
        total_children = 100
        batch_size = 5
        donation_amount = 1
        donations_per_child = 10

        used_ids = set()

        # Create children with 10 × ₪1 donations each
        for i in range(total_children):
            ident = f"{i:05d}"
            child = _make_child(f"child{i}")
            for j in range(donations_per_child):
                DonationTransaction.objects.create(
                    child=child,
                    category=self.category,
                    amount=donation_amount,
                    date_donated=self.week_ago + timedelta(minutes=(i * donations_per_child + j))
                )

        # Perform 20 rounds of spending ₪5 (5 children per round)
        for round_index in range(20):
            spending = DonationSpendingUtils.spend_from_category_fair(
                category=self.category,
                amount=batch_size,
                note=f"round {round_index}",
                shop=self.shop
            )

            batch_child_ids = list(
                SpendingAllocation.objects.filter(spending=spending)
                .values_list("transaction__child_id", flat=True)
                .distinct()
            )

            # Check batch size
            self.assertEqual(len(batch_child_ids), batch_size, f"Batch {round_index} size mismatch")

            # Check order consistency (must be sorted by child id for first cycle)
            self.assertEqual(sorted(batch_child_ids), batch_child_ids, f"Batch {round_index} not in order")

            # Check that no child is repeated before full cycle completes
            for cid in batch_child_ids:
                if cid in used_ids:
                    self.fail(f"Child {cid} selected again before full rotation in round {round_index}")
                used_ids.add(cid)

            # Reset used_ids after a full rotation
            if len(used_ids) == total_children:
                used_ids.clear()
                
                
    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_total_allocation_matches_amount(self, mock_pts):
        """sum(amount_used) must equal spending.amount_spent for diverse amounts."""
        mock_pts.return_value = 1_000
        child = _make_child("sumKid")
        # 3 donations totalling 120
        DonationTransaction.objects.bulk_create([
            DonationTransaction(child=child, category=self.category, amount=40, date_donated=self.week_ago),
            DonationTransaction(child=child, category=self.category, amount=50, date_donated=self.day_ago),
            DonationTransaction(child=child, category=self.category, amount=30, date_donated=self.now),
        ])

        for amount in (10, 65, 25, 20):   # 4 separate spendings, total 120
            spending = DonationSpendingUtils.spend_from_category_fair(
                category=self.category, amount=amount, shop=self.shop, note=f"amount {amount}"
            )
            total_alloc = SpendingAllocation.objects.filter(spending=spending).aggregate(
                s=Sum("amount_used")
            )["s"]
            self.assertEqual(total_alloc, amount, f"Allocation sum mismatch for amount {amount}")


    @patch("shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month")
    def test_fifo_order_inside_child(self, mock_pts):
        """Ensure child allocations consume donations oldest-first."""
        mock_pts.return_value = 1_000
        fifo_child = _make_child("fifoKid")

        t1 = DonationTransaction.objects.create(child=fifo_child, category=self.category, amount=30, date_donated=self.week_ago)
        t2 = DonationTransaction.objects.create(child=fifo_child, category=self.category, amount=30, date_donated=self.day_ago)
        t3 = DonationTransaction.objects.create(child=fifo_child, category=self.category, amount=30, date_donated=self.now)

        spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category, amount=70, note="FIFO test", shop=self.shop
        )
        alloc_tx_ids = list(
            SpendingAllocation.objects.filter(spending=spending)
            .values_list("transaction_id", flat=True)
        )

        # Expected order: first t1, then t2, finally t3 (partial)
        self.assertEqual(alloc_tx_ids[0], t1.id)
        self.assertEqual(alloc_tx_ids[1], t2.id)
        # The third allocation (if split) must be t3
        if len(alloc_tx_ids) > 2:
            self.assertEqual(alloc_tx_ids[2], t3.id)
