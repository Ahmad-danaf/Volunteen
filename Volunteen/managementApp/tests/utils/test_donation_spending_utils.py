from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from managementApp.utils.DonationSpendingUtils import DonationSpendingUtils
from managementApp.models import DonationCategory, DonationTransaction, DonationSpending, SpendingAllocation
from childApp.models import Child
from shopApp.models import Shop
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction


class DonationSpendingUtilsTests(TestCase):
    """Tests for the DonationSpendingUtils utility class."""

    def setUp(self):
        """Set up test data for the tests."""
        self.user1 = User.objects.create_user(username='testchild1', password='password123')
        self.user2 = User.objects.create_user(username='testchild2', password='password123')
        
        self.child1 = Child.objects.create(user=self.user1, points=100, identifier='CH001', secret_code='123')
        self.child2 = Child.objects.create(user=self.user2, points=200, identifier='CH002', secret_code='456')
        
        self.category1 = DonationCategory.objects.create(
            name='Education',
            description='Donations for educational activities',
            is_active=True
        )
        self.category2 = DonationCategory.objects.create(
            name='Health',
            description='Donations for health-related activities',
            is_active=True
        )
        
        # Create a shop user
        self.shop_user = User.objects.create_user(username='testshop', password='password123')
        
        # Create a shop with valid fields
        self.shop = Shop.objects.create(
            user=self.shop_user,
            name='Test Shop',
            max_points=1000
        )
        
        # Set the current time for the tests
        self.now = timezone.now()
        self.one_day_ago = self.now - timedelta(days=1)
        self.one_week_ago = self.now - timedelta(days=7)
        
        # Create donation transactions
        with patch('django.utils.timezone.now', return_value=self.one_week_ago):
            self.donation1 = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category1,
                amount=100,
                note='Test donation 1'
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_day_ago):
            self.donation2 = DonationTransaction.objects.create(
                child=self.child2,
                category=self.category1,
                amount=200,
                note='Test donation 2'
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_day_ago):
            self.donation3 = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category2,
                amount=150,
                note='Test donation 3'
            )

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_valid(self, mock_get_remaining_points):
        """Test spend_from_category with valid inputs."""
        # Mock the shop manager to return enough points
        mock_get_remaining_points.return_value = 500
        
        # Spend some from category1
        spending = DonationSpendingUtils.spend_from_category(
            category=self.category1,
            amount=75,
            note="Test spending",
            shop=self.shop
        )
        
        # Verify the spending was created correctly
        self.assertEqual(spending.category, self.category1)
        self.assertEqual(spending.shop, self.shop)
        self.assertEqual(spending.amount_spent, 75)
        self.assertEqual(spending.note, "Test spending")
        
        # Verify allocations were created in FIFO order
        allocations = SpendingAllocation.objects.filter(spending=spending).order_by('transaction__date_donated')
        
        # Should only use one allocation for the oldest transaction
        self.assertEqual(allocations.count(), 1)
        self.assertEqual(allocations[0].transaction, self.donation1)
        self.assertEqual(allocations[0].amount_used, 75)
        
        # Check the category leftover is correctly calculated
        leftover = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover, 300 - 75)  # 300 total donated - 75 spent = 225

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_multiple_allocations(self, mock_get_remaining_points):
        """Test spend_from_category when it needs to use multiple transactions."""
        # Mock the shop manager to return enough points
        mock_get_remaining_points.return_value = 1000
        
        # Spend an amount that requires both donations
        spending = DonationSpendingUtils.spend_from_category(
            category=self.category1,
            amount=150,
            note="Test spending",
            shop=self.shop
        )
        
        # Verify spending record
        self.assertEqual(spending.amount_spent, 150)
        
        # Verify allocations 
        allocations = SpendingAllocation.objects.filter(spending=spending).order_by('transaction__date_donated')
        
        # Should use two transactions
        self.assertEqual(allocations.count(), 2)
        
        # First allocation should use all of donation1 (100)
        self.assertEqual(allocations[0].transaction, self.donation1)
        self.assertEqual(allocations[0].amount_used, 100)
        
        # Second allocation should use part of donation2 (50)
        self.assertEqual(allocations[1].transaction, self.donation2)
        self.assertEqual(allocations[1].amount_used, 50)
        
        # Verify leftover
        leftover = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover, 300 - 150)  # 300 total - 150 spent = 150

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_insufficient_funds(self, mock_get_remaining_points):
        """Test spend_from_category with insufficient funds."""
        # Mock the shop manager to return enough points
        mock_get_remaining_points.return_value = 1000
        
        # Try to spend more than available
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category(
                category=self.category1,
                amount=500,  # Only have 300 total
                note="Test spending",
                shop=self.shop
            )
        
        self.assertIn("Not enough donations", str(context.exception))
        
        # Verify no spending record was created
        self.assertEqual(DonationSpending.objects.count(), 0)
        
        # Verify no allocations were made
        self.assertEqual(SpendingAllocation.objects.count(), 0)

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_insufficient_shop_points(self, mock_get_remaining_points):
        """Test spend_from_category with insufficient shop points."""
        # Mock the shop manager to return NOT enough points
        mock_get_remaining_points.return_value = 50  # Only 50 points left
        
        # Try to spend an amount the shop doesn't have enough points for
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category(
                category=self.category1,
                amount=100,
                note="Test spending",
                shop=self.shop
            )
        
        self.assertIn("doesn't have enough points", str(context.exception))
        
        # Verify no spending or allocations created
        self.assertEqual(DonationSpending.objects.count(), 0)
        self.assertEqual(SpendingAllocation.objects.count(), 0)

    def test_spend_from_category_zero_amount(self):
        """Test spend_from_category with zero amount."""
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category(
                category=self.category1,
                amount=0,
                note="Zero amount",
                shop=self.shop
            )
        
        self.assertIn("must be positive", str(context.exception))

    def test_get_category_leftover(self):
        """Test get_category_leftover returns correct value."""
        # Initially should be total donations (no spending yet)
        leftover1 = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover1, 300)  # 100 + 200
        
        leftover2 = DonationSpendingUtils.get_category_leftover(self.category2)
        self.assertEqual(leftover2, 150)
        
        # Add a spending allocation and check again
        spending = DonationSpending.objects.create(
            category=self.category1, 
            amount_spent=50,
            note="Test spending"
        )
        
        # Create allocation
        allocation = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation1,
            amount_used=50
        )
        
        # Check leftover after spending
        leftover1_after = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover1_after, 250)  # 300 - 50 = 250

    def test_get_recent_spendings(self):
        """Test get_recent_spendings returns spendings in correct order."""
        # Create spendings with different dates
        with patch('django.utils.timezone.now', return_value=self.one_week_ago):
            spending1 = DonationSpending.objects.create(
                category=self.category1,
                amount_spent=50,
                note="Spending 1 (oldest)"
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_day_ago):
            spending2 = DonationSpending.objects.create(
                category=self.category2,
                amount_spent=75,
                note="Spending 2"
            )
        
        with patch('django.utils.timezone.now', return_value=self.now):
            spending3 = DonationSpending.objects.create(
                category=self.category1,
                amount_spent=25,
                note="Spending 3 (newest)"
            )
        
        # Get recent spendings with default limit
        recent = DonationSpendingUtils.get_recent_spendings()
        
        # Should return all 3 in reverse chronological order
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0].id, spending3.id)  # Newest first
        self.assertEqual(recent[1].id, spending2.id)
        self.assertEqual(recent[2].id, spending1.id)  # Oldest last
        
        # Test with a smaller limit
        recent_limited = DonationSpendingUtils.get_recent_spendings(limit=2)
        self.assertEqual(len(recent_limited), 2)
        self.assertEqual(recent_limited[0].id, spending3.id)
        self.assertEqual(recent_limited[1].id, spending2.id)

    def test_get_spending_details(self):
        """Test get_spending_details returns correct structure."""
        # Create a spending with allocations
        spending = DonationSpending.objects.create(
            category=self.category1,
            shop=self.shop,
            amount_spent=150,
            note="Test spending details"
        )
        
        # Create allocations from multiple transactions
        allocation1 = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation1,
            amount_used=100
        )
        
        allocation2 = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation2,
            amount_used=50
        )
        
        # Get details
        details = DonationSpendingUtils.get_spending_details(spending.id)
        
        # Verify structure and content
        self.assertEqual(details['spending_id'], spending.id)
        self.assertEqual(details['category'], self.category1.name)
        self.assertEqual(details['amount_spent'], 150)
        self.assertEqual(details['note'], "Test spending details")
        
        # Check shop info
        self.assertIsNotNone(details['shop'])
        self.assertEqual(details['shop']['name'], self.shop.name)
        
        # Check allocations
        allocations = details['allocations']
        self.assertEqual(len(allocations), 2)
        
        # First allocation
        self.assertEqual(allocations[0]['donation_transaction_id'], self.donation1.id)
        self.assertEqual(allocations[0]['child_username'], self.child1.user.username)
        self.assertEqual(allocations[0]['amount_used'], 100)
        
        # Second allocation
        self.assertEqual(allocations[1]['donation_transaction_id'], self.donation2.id)
        self.assertEqual(allocations[1]['child_username'], self.child2.user.username)
        self.assertEqual(allocations[1]['amount_used'], 50)

    def test_get_spending_details_nonexistent(self):
        """Test get_spending_details with nonexistent ID."""
        # Use a non-existent ID
        details = DonationSpendingUtils.get_spending_details(9999)
        self.assertIsNone(details)

    def test_get_total_leftover_all_categories(self):
        """Test get_total_leftover_all_categories correctly aggregates leftovers."""
        # Initially total is sum of all donations
        total_leftover = DonationSpendingUtils.get_total_leftover_all_categories()
        self.assertEqual(total_leftover, 450)  # 100 + 200 + 150 = 450
        
        # Create a spending with allocation
        spending = DonationSpending.objects.create(
            category=self.category1,
            amount_spent=75,
            note="Test spending"
        )
        
        allocation = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation1,
            amount_used=75
        )
        
        # Check total leftover after spending
        total_leftover_after = DonationSpendingUtils.get_total_leftover_all_categories()
        self.assertEqual(total_leftover_after, 375)  # 450 - 75 = 375

    def test_get_leftover_by_category(self):
        """Test get_leftover_by_category returns correct structure and values."""
        # Create a spending with allocation
        spending = DonationSpending.objects.create(
            category=self.category1,
            amount_spent=40,
            note="Test spending"
        )
        
        allocation = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation1,
            amount_used=40
        )
        
        # Get leftovers by category
        leftovers = DonationSpendingUtils.get_leftover_by_category()
        
        # Should return all active categories
        self.assertEqual(len(leftovers), 2)
        
        # Verify structure and values
        for item in leftovers:
            category = item['category']
            leftover = item['leftover']
            
            if category.id == self.category1.id:
                # Category 1: 300 total - 40 spent = 260
                self.assertEqual(leftover, 260)
            elif category.id == self.category2.id:
                # Category 2: 150 total - 0 spent = 150
                self.assertEqual(leftover, 150)
            else:
                self.fail(f"Unexpected category in results: {category.name}")

    def test_transaction_atomic(self):
        """Test that spend_from_category uses transaction.atomic correctly."""
        # Instead of a complex mock, let's use a simple approach: try to spend more than available,
        # which should be wrapped in transaction.atomic and thus roll back completely
        
        # First, spend part of donation1
        spending = DonationSpending.objects.create(
            category=self.category1,
            amount_spent=30,
            note="Initial spending"
        )
        
        allocation = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation1,
            amount_used=30
        )
        
        # Verify initial state
        self.assertEqual(DonationSpending.objects.count(), 1)
        self.assertEqual(SpendingAllocation.objects.count(), 1)
        
        # Now attempt to spend more than available, which should fail
        with self.assertRaises(ValueError):
            with patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month', return_value=1000):
                DonationSpendingUtils.spend_from_category(
                    category=self.category1,
                    amount=500,  # More than the 300-30=270 available
                    note="Should fail",
                    shop=self.shop
                )
        
        # Verify no additional spending records were created (transaction rolled back)
        self.assertEqual(DonationSpending.objects.count(), 1)  # Still just the first one
        self.assertEqual(SpendingAllocation.objects.count(), 1)  # Still just the first allocation 
        
     #start here   
    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_fair_valid(self, mock_get_remaining_points):
        """Test spend_from_category_fair with valid inputs and round-robin logic."""
        mock_get_remaining_points.return_value = 1000
        
        # Spend 150 from category1
        spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category1,
            amount=150,
            note="Fair spending",
            shop=self.shop
        )
        
        self.assertEqual(spending.category, self.category1)
        self.assertEqual(spending.shop, self.shop)
        self.assertEqual(spending.amount_spent, 150)
        self.assertEqual(spending.note, "Fair spending")
        
        allocations = SpendingAllocation.objects.filter(spending=spending).order_by('id')
        self.assertEqual(allocations.count(), 2)
        
        # First allocation should use donation1 (child1)
        self.assertEqual(allocations[0].transaction, self.donation1)
        self.assertEqual(allocations[0].amount_used, 100)
        
        # Second allocation should use donation2 (child2)
        self.assertEqual(allocations[1].transaction, self.donation2)
        self.assertEqual(allocations[1].amount_used, 50)
        
        # Verify leftover
        leftover = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover, 300 - 150)  # 300 total - 150 spent = 150

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_fair_multiple_rounds(self, mock_get_remaining_points):
        """
        Fair allocator should stop once requested amount reached—even if not all
        transactions were consumed. Here only two allocations are needed (100+200).
        """
        mock_get_remaining_points.return_value = 1000

        extra_donation = DonationTransaction.objects.create(
            child=self.child1,
            category=self.category1,
            amount=50,
            note="Extra donation for fairness"
        )

        spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category1,
            amount=300,
            note="Full rotation spending",
            shop=self.shop
        )

        allocations = list(
            SpendingAllocation.objects.filter(spending=spending).order_by('id')
        )
        self.assertEqual(len(allocations), 2)

        # 1) child1’s first donation
        self.assertEqual(allocations[0].transaction, self.donation1)
        self.assertEqual(allocations[0].amount_used, 100)

        # 2) child2’s donation
        self.assertEqual(allocations[1].transaction, self.donation2)
        self.assertEqual(allocations[1].amount_used, 200)

        # Extra donation left untouched → 50 coins still in the pool
        self.assertEqual(
            DonationSpendingUtils.get_category_leftover(self.category1),
            50
        )

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_fair_insufficient_funds(self, mock_get_remaining_points):
        """Test spend_from_category_fair with insufficient category funds."""
        mock_get_remaining_points.return_value = 1000
        
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category_fair(
                category=self.category1,
                amount=500,  # Only have 300
                note="Should fail (fair)",
                shop=self.shop
            )
        
        self.assertIn("Not enough donations", str(context.exception))
        self.assertEqual(DonationSpending.objects.count(), 0)
        self.assertEqual(SpendingAllocation.objects.count(), 0)

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_spend_from_category_fair_insufficient_shop_points(self, mock_get_remaining_points):
        """Test spend_from_category_fair with insufficient shop points."""
        mock_get_remaining_points.return_value = 50  # Not enough
        
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category_fair(
                category=self.category1,
                amount=100,
                note="Shop points fail (fair)",
                shop=self.shop
            )
        
        self.assertIn("doesn't have enough points", str(context.exception))
        self.assertEqual(DonationSpending.objects.count(), 0)
        self.assertEqual(SpendingAllocation.objects.count(), 0)

    def test_spend_from_category_fair_zero_amount(self):
        """Test spend_from_category_fair with zero amount."""
        with self.assertRaises(ValueError) as context:
            DonationSpendingUtils.spend_from_category_fair(
                category=self.category1,
                amount=0,
                note="Zero amount (fair)",
                shop=self.shop
            )
        
        self.assertIn("must be positive", str(context.exception))


    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_fifo_then_fair(self, mock_get_remaining_points):
        """
        FIFO spending first, then fair spending should respect leftovers and rotation.
        After FIFO(125) only child2 has balance → fair allocator should make ONE allocation.
        """
        mock_get_remaining_points.return_value = 1000

        # FIFO spend 125 (100 child1 + 25 child2)
        DonationSpendingUtils.spend_from_category(
            category=self.category1,
            amount=125,
            note="FIFO first",
            shop=self.shop
        )

        # Fair spend 100 – only child2 has remaining coins
        fair_spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category1,
            amount=100,
            note="Fair second",
            shop=self.shop
        )

        fair_allocs = list(
            SpendingAllocation.objects.filter(spending=fair_spending).order_by('id')
        )
        self.assertEqual(len(fair_allocs), 1)
        self.assertEqual(fair_allocs[0].transaction, self.donation2)
        self.assertEqual(fair_allocs[0].amount_used, 100)

        # Leftover should now be 75 (300-125-100)
        self.assertEqual(
            DonationSpendingUtils.get_category_leftover(self.category1),
            75
        )

    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    def test_fair_then_fifo(self, mock_get_remaining_points):
        """Fair spending first, then FIFO spending should consume remaining coins oldest-first."""
        mock_get_remaining_points.return_value = 1000

        # 1️⃣ Fair spend 150 (child1 -> child2 order)
        fair_spending = DonationSpendingUtils.spend_from_category_fair(
            category=self.category1,
            amount=150,
            note="Fair first",
            shop=self.shop
        )

        # 2️⃣ FIFO spend the remaining 150
        fifo_spending = DonationSpendingUtils.spend_from_category(
            category=self.category1,
            amount=150,
            note="FIFO second",
            shop=self.shop
        )

        # --- Assertions ---
        fair_allocs = list(
            SpendingAllocation.objects.filter(spending=fair_spending).order_by('id')
        )
        self.assertEqual(fair_allocs[0].transaction, self.donation1)   # 100
        self.assertEqual(fair_allocs[1].transaction, self.donation2)   # 50

        fifo_allocs = list(
            SpendingAllocation.objects.filter(spending=fifo_spending).order_by('id')
        )
        # After fair spending, donation1 is exhausted. FIFO should start with remaining of donation2.
        self.assertEqual(len(fifo_allocs), 1)
        self.assertEqual(fifo_allocs[0].transaction, self.donation2)
        self.assertEqual(fifo_allocs[0].amount_used, 150)

        # No coins left
        leftover = DonationSpendingUtils.get_category_leftover(self.category1)
        self.assertEqual(leftover, 0)

    