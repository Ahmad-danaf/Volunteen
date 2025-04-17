from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from datetime import datetime, timedelta

from managementApp.models import (
    DonationCategory,
    DonationTransaction,
    DonationSpending,
    SpendingAllocation
)
from childApp.models import Child
from shopApp.models import Shop
from django.contrib.auth.models import User


class DonationCategoryModelTests(TestCase):
    """Tests for the DonationCategory model."""

    def setUp(self):
        """Set up test data for the tests."""
        self.category = DonationCategory.objects.create(
            name='Education',
            description='Donations for educational activities',
            is_active=True
        )

    def test_string_representation(self):
        """Test the string representation of a DonationCategory."""
        self.assertEqual(str(self.category), 'Education')

    def test_create_category_with_defaults(self):
        """Test creating a category with default values."""
        category = DonationCategory.objects.create(
            name='Test Category'
        )
        self.assertEqual(category.name, 'Test Category')
        self.assertIsNone(category.description)
        self.assertTrue(category.is_active)  # Default is True
        self.assertEqual(category.img, 'defaults/no-image.png')  # Default image

    def test_create_inactive_category(self):
        """Test creating an inactive category."""
        inactive_category = DonationCategory.objects.create(
            name='Inactive Category',
            description='This category is not active',
            is_active=False
        )
        self.assertFalse(inactive_category.is_active)
        
        # Verify it's not included in the active categories queryset
        active_categories = DonationCategory.objects.filter(is_active=True)
        self.assertNotIn(inactive_category, active_categories)
        self.assertIn(self.category, active_categories)


class DonationTransactionModelTests(TestCase):
    """Tests for the DonationTransaction model."""

    def setUp(self):
        """Set up test data for the tests."""
        self.user = User.objects.create_user(username='testchild', password='password123')
        self.child = Child.objects.create(user=self.user, points=100, identifier='CH001', secret_code='123')
        self.category = DonationCategory.objects.create(
            name='Education',
            description='Donations for educational activities',
            is_active=True
        )
        
        # Create a donation with a fixed time for predictable testing
        self.test_time = timezone.now()
        with patch('django.utils.timezone.now', return_value=self.test_time):
            self.donation = DonationTransaction.objects.create(
                child=self.child,
                category=self.category,
                amount=100,
                note='Test donation'
            )

    def test_string_representation(self):
        """Test the string representation of a DonationTransaction."""
        expected = f"{self.child} donated {self.donation.amount} to {self.category}"
        self.assertEqual(str(self.donation), expected)

    def test_create_donation_with_required_fields(self):
        """Test creating a donation with only the required fields."""
        donation = DonationTransaction.objects.create(
            child=self.child,
            category=self.category,
            amount=50
        )
        self.assertEqual(donation.child, self.child)
        self.assertEqual(donation.category, self.category)
        self.assertEqual(donation.amount, 50)
        self.assertIsNone(donation.note)
        
        # Verify date_donated was set automatically
        self.assertIsNotNone(donation.date_donated)
        self.assertIsInstance(donation.date_donated, datetime)

    def test_date_donated_auto_now_add(self):
        """Test that date_donated field is automatically set on creation."""
        # Verify that the date_donated matches our mocked time
        self.assertEqual(self.donation.date_donated, self.test_time)
        
        # Create another donation with a different time
        new_time = self.test_time + timedelta(days=1)
        with patch('django.utils.timezone.now', return_value=new_time):
            new_donation = DonationTransaction.objects.create(
                child=self.child,
                category=self.category,
                amount=75
            )
        
        # Verify new_donation has the new time
        self.assertEqual(new_donation.date_donated, new_time)
        
        # Original donation still has the original time
        self.assertEqual(self.donation.date_donated, self.test_time)


class DonationSpendingModelTests(TestCase):
    """Tests for the DonationSpending model."""

    def setUp(self):
        """Set up test data for the tests."""
        self.category = DonationCategory.objects.create(
            name='Education',
            description='Donations for educational activities',
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
        
        # Create a spending with a fixed time
        self.test_time = timezone.now()
        with patch('django.utils.timezone.now', return_value=self.test_time):
            self.spending = DonationSpending.objects.create(
                category=self.category,
                shop=self.shop,
                amount_spent=100,
                note='Test spending'
            )

    def test_string_representation(self):
        """Test the string representation of a DonationSpending."""
        expected = f"Spent {self.spending.amount_spent} in {self.category.name}"
        self.assertEqual(str(self.spending), expected)

    def test_create_spending_with_required_fields(self):
        """Test creating a spending with only the required fields."""
        spending = DonationSpending.objects.create(
            category=self.category,
            amount_spent=50
        )
        self.assertEqual(spending.category, self.category)
        self.assertEqual(spending.amount_spent, 50)
        self.assertIsNone(spending.shop)
        self.assertIsNone(spending.note)
        
        # Verify date_spent was set automatically
        self.assertIsNotNone(spending.date_spent)
        self.assertIsInstance(spending.date_spent, datetime)

    def test_date_spent_auto_now_add(self):
        """Test that date_spent field is automatically set on creation."""
        # Verify that the date_spent matches our mocked time
        self.assertEqual(self.spending.date_spent, self.test_time)
        
        # Create another spending with a different time
        new_time = self.test_time + timedelta(days=1)
        with patch('django.utils.timezone.now', return_value=new_time):
            new_spending = DonationSpending.objects.create(
                category=self.category,
                amount_spent=75
            )
        
        # Verify new_spending has the new time
        self.assertEqual(new_spending.date_spent, new_time)
        
        # Original spending still has the original time
        self.assertEqual(self.spending.date_spent, self.test_time)

    def test_spending_with_and_without_shop(self):
        """Test creating spendings with and without a shop."""
        # Spending with a shop (already created in setUp)
        self.assertEqual(self.spending.shop, self.shop)
        
        # Spending without a shop
        spending_no_shop = DonationSpending.objects.create(
            category=self.category,
            amount_spent=50,
            note='Spending without shop'
        )
        self.assertIsNone(spending_no_shop.shop)


class SpendingAllocationModelTests(TestCase):
    """Tests for the SpendingAllocation model."""

    def setUp(self):
        """Set up test data for the tests."""
        # Create user, child, category
        self.user = User.objects.create_user(username='testchild', password='password123')
        self.child = Child.objects.create(user=self.user, points=100, identifier='CH001', secret_code='123')
        self.category = DonationCategory.objects.create(
            name='Education',
            description='Donations for educational activities',
            is_active=True
        )
        
        # Create a donation
        self.donation = DonationTransaction.objects.create(
            child=self.child,
            category=self.category,
            amount=100,
            note='Test donation'
        )
        
        # Create a spending
        self.spending = DonationSpending.objects.create(
            category=self.category,
            amount_spent=75,
            note='Test spending'
        )
        
        # Create an allocation
        self.allocation = SpendingAllocation.objects.create(
            spending=self.spending,
            transaction=self.donation,
            amount_used=75
        )

    def test_string_representation(self):
        """Test the string representation of a SpendingAllocation."""
        expected = f"{self.allocation.amount_used} spent from {self.donation}"
        self.assertEqual(str(self.allocation), expected)

    def test_create_allocation(self):
        """Test creating an allocation with all fields."""
        # Create a new donation and spending
        donation = DonationTransaction.objects.create(
            child=self.child,
            category=self.category,
            amount=200
        )
        
        spending = DonationSpending.objects.create(
            category=self.category,
            amount_spent=100
        )
        
        # Create a new allocation
        allocation = SpendingAllocation.objects.create(
            spending=spending,
            transaction=donation,
            amount_used=100
        )
        
        self.assertEqual(allocation.spending, spending)
        self.assertEqual(allocation.transaction, donation)
        self.assertEqual(allocation.amount_used, 100)

    def test_multiple_allocations_per_spending(self):
        """Test that a spending can have multiple allocations."""
        # Create another donation
        donation2 = DonationTransaction.objects.create(
            child=self.child,
            category=self.category,
            amount=100
        )
        
        # Create another spending
        spending = DonationSpending.objects.create(
            category=self.category,
            amount_spent=150  # Will need multiple allocations
        )
        
        # Create two allocations for this spending
        allocation1 = SpendingAllocation.objects.create(
            spending=spending,
            transaction=self.donation,
            amount_used=75  # Part of first donation
        )
        
        allocation2 = SpendingAllocation.objects.create(
            spending=spending,
            transaction=donation2,
            amount_used=75  # Part of second donation
        )
        
        # Get all allocations for this spending
        allocations = SpendingAllocation.objects.filter(spending=spending)
        
        # Verify there are exactly 2 allocations
        self.assertEqual(allocations.count(), 2)
        
        # Verify total amount_used equals the spending's amount_spent
        total_used = sum(a.amount_used for a in allocations)
        self.assertEqual(total_used, spending.amount_spent)

    def test_multiple_allocations_per_transaction(self):
        """Test that a donation transaction can be used for multiple spendings."""
        # Create another spending
        spending2 = DonationSpending.objects.create(
            category=self.category,
            amount_spent=25  # Will use remaining amount from the donation
        )
        
        # Create another allocation using the same donation
        allocation2 = SpendingAllocation.objects.create(
            spending=spending2,
            transaction=self.donation,
            amount_used=25  # Remaining from first donation (100 - 75 = 25)
        )
        
        # Get all allocations for this transaction
        allocations = SpendingAllocation.objects.filter(transaction=self.donation)
        
        # Verify there are exactly 2 allocations
        self.assertEqual(allocations.count(), 2)
        
        # Verify total amount_used is not more than the donation amount
        total_used = sum(a.amount_used for a in allocations)
        self.assertLessEqual(total_used, self.donation.amount)
        # In this case, should be equal since we used the entire amount
        self.assertEqual(total_used, 100) 