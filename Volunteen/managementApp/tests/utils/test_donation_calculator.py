from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from datetime import datetime, timedelta
import io
import csv

from managementApp.utils.DonationCalculator import DonationCalculator
from managementApp.models import DonationCategory, DonationTransaction, DonationSpending
from childApp.models import Child
from django.contrib.auth.models import User


class DonationCalculatorTests(TestCase):
    """Tests for the DonationCalculator utility class."""

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
        
        # Set the current time for the tests
        self.now = timezone.now()
        self.one_day_ago = self.now - timedelta(days=1)
        self.one_week_ago = self.now - timedelta(days=7)
        self.one_month_ago = self.now - timedelta(days=30)
        
        # Create donation transactions
        with patch('django.utils.timezone.now', return_value=self.one_day_ago):
            self.donation1 = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category1,
                amount=100,
                note='Test donation 1'
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_week_ago):
            self.donation2 = DonationTransaction.objects.create(
                child=self.child2,
                category=self.category1,
                amount=200,
                note='Test donation 2'
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_month_ago):
            self.donation3 = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category2,
                amount=150,
                note='Test donation 3'
            )
        
        # Create donation spending
        with patch('django.utils.timezone.now', return_value=self.one_week_ago):
            self.spending1 = DonationSpending.objects.create(
                category=self.category1,
                amount_spent=50,
                note='Test spending 1'
            )
        
        with patch('django.utils.timezone.now', return_value=self.one_day_ago):
            self.spending2 = DonationSpending.objects.create(
                category=self.category2,
                amount_spent=30,
                note='Test spending 2'
            )

    def test_get_total_donated_no_filters(self):
        """Test get_total_donated without any filters."""
        # Total of all donations: 100 + 200 + 150 = 450
        total = DonationCalculator.get_total_donated()
        self.assertEqual(total, 450)

    def test_get_total_donated_by_category(self):
        """Test get_total_donated filtered by category."""
        # Category 1: 100 + 200 = 300
        total_cat1 = DonationCalculator.get_total_donated(category=self.category1)
        self.assertEqual(total_cat1, 300)
        
        # Category 2: 150
        total_cat2 = DonationCalculator.get_total_donated(category=self.category2)
        self.assertEqual(total_cat2, 150)

    def test_get_total_donated_by_date_range(self):
        """Test get_total_donated filtered by date range."""
        # Test only recent donations (last 3 days)
        three_days_ago = self.now - timedelta(days=3)
        recent_total = DonationCalculator.get_total_donated(start_date=three_days_ago)
        # Only donation1 (100 coins) should be included
        self.assertEqual(recent_total, 100)
        
        # Test between one week and three days ago
        one_week_three_days = DonationCalculator.get_total_donated(
            start_date=self.one_week_ago,
            end_date=three_days_ago
        )
        # Only donation2 (200 coins) should be included
        self.assertEqual(one_week_three_days, 200)

    def test_get_total_donated_no_donations(self):
        """Test get_total_donated when there are no matching donations."""
        # Create a new inactive category with no donations
        inactive_category = DonationCategory.objects.create(
            name='Inactive',
            description='Inactive category',
            is_active=False
        )
        
        # Should return 0 when no donations match the filter
        total = DonationCalculator.get_total_donated(category=inactive_category)
        self.assertEqual(total, 0)

    def test_get_total_spent_no_filters(self):
        """Test get_total_spent without any filters."""
        # Total of all spendings: 50 + 30 = 80
        total = DonationCalculator.get_total_spent()
        self.assertEqual(total, 80)

    def test_get_total_spent_by_category(self):
        """Test get_total_spent filtered by category."""
        # Category 1: 50
        total_cat1 = DonationCalculator.get_total_spent(category=self.category1)
        self.assertEqual(total_cat1, 50)
        
        # Category 2: 30
        total_cat2 = DonationCalculator.get_total_spent(category=self.category2)
        self.assertEqual(total_cat2, 30)

    def test_get_total_spent_by_date_range(self):
        """Test get_total_spent filtered by date range."""
        # Test only recent spendings (last 3 days)
        three_days_ago = self.now - timedelta(days=3)
        recent_total = DonationCalculator.get_total_spent(start_date=three_days_ago)
        # Only spending2 (30 coins) should be included
        self.assertEqual(recent_total, 30)

    def test_get_category_summary(self):
        """Test get_category_summary returns correct data."""
        summaries = DonationCalculator.get_category_summary()
        
        # Should return data for both active categories
        self.assertEqual(len(summaries), 2)
        
        # Verify each summary has the correct structure and values
        for summary in summaries:
            category = summary['category']
            if category.id == self.category1.id:
                # Education: donated=300, spent=50, leftover=250
                self.assertEqual(summary['total_donated'], 300)
                self.assertEqual(summary['total_spent'], 50)
                self.assertEqual(summary['leftover'], 250)
            elif category.id == self.category2.id:
                # Health: donated=150, spent=30, leftover=120
                self.assertEqual(summary['total_donated'], 150)
                self.assertEqual(summary['total_spent'], 30)
                self.assertEqual(summary['leftover'], 120)

    def test_get_category_summary_with_date_range(self):
        """Test get_category_summary with date filters."""
        # Get summary for only the past 3 days
        three_days_ago = self.now - timedelta(days=3)
        summaries = DonationCalculator.get_category_summary(start_date=three_days_ago)
        
        # Verify each summary has the correct values for the date range
        for summary in summaries:
            category = summary['category']
            if category.id == self.category1.id:
                # Only donation1 (100) and no spendings in this period
                self.assertEqual(summary['total_donated'], 100)
                self.assertEqual(summary['total_spent'], 0)
                self.assertEqual(summary['leftover'], 100)
            elif category.id == self.category2.id:
                # No donations and spending2 (30) in this period
                self.assertEqual(summary['total_donated'], 0)
                self.assertEqual(summary['total_spent'], 30)
                self.assertEqual(summary['leftover'], -30)

    @patch('django.utils.timezone.now')
    def test_get_monthly_donations_by_category(self, mock_now):
        """Test get_monthly_donations_by_category returns correct data."""
        # Setup a fixed year
        test_year = 2023
        mock_now.return_value = timezone.make_aware(datetime(test_year, 12, 15))
        
        # Create donations for different months in the test year
        jan_date = timezone.make_aware(datetime(test_year, 1, 15))
        mar_date = timezone.make_aware(datetime(test_year, 3, 15))
        dec_date = timezone.make_aware(datetime(test_year, 12, 1))
        
        with patch('django.utils.timezone.now', return_value=jan_date):
            jan_donation = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category1,
                amount=50,
                note='January donation'
            )
        
        with patch('django.utils.timezone.now', return_value=mar_date):
            mar_donation = DonationTransaction.objects.create(
                child=self.child2,
                category=self.category1,
                amount=75,
                note='March donation'
            )
        
        with patch('django.utils.timezone.now', return_value=dec_date):
            dec_donation = DonationTransaction.objects.create(
                child=self.child1,
                category=self.category2,
                amount=100,
                note='December donation'
            )
        
        # Get monthly donations
        monthly_data = DonationCalculator.get_monthly_donations_by_category(test_year)
        
        # Verify structure and content
        self.assertIn(self.category1.id, monthly_data)
        self.assertIn(self.category2.id, monthly_data)
        
        cat1_data = monthly_data[self.category1.id]
        cat2_data = monthly_data[self.category2.id]
        
        # Check category objects are correct
        self.assertEqual(cat1_data['category'].id, self.category1.id)
        self.assertEqual(cat2_data['category'].id, self.category2.id)
        
        # Check monthly totals arrays have 12 elements
        self.assertEqual(len(cat1_data['monthly_totals']), 12)
        self.assertEqual(len(cat2_data['monthly_totals']), 12)
        
        # Check specific months have correct totals
        self.assertEqual(cat1_data['monthly_totals'][0], 50)  # January (index 0) = 50
        self.assertEqual(cat1_data['monthly_totals'][2], 75)  # March (index 2) = 75
        self.assertEqual(cat2_data['monthly_totals'][11], 100)  # December (index 11) = 100

    def test_export_donations_report(self):
        """Test export_donations_report generates a valid CSV."""
        # Get the report as a string
        csv_data = DonationCalculator.export_donations_report()
        
        # Parse the CSV
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)
        
        # Verify header row
        self.assertEqual(rows[0], ["Donation ID", "Child Username", "Category", "Amount", "Date Donated", "Note"])
        
        # Verify data rows (should have 3 donations + 1 header = 4 rows)
        self.assertEqual(len(rows), 4)
        
        # Check specific donation data is in the report
        # Data should be ordered by date_donated
        self.assertEqual(int(rows[1][0]), self.donation3.id)  # Oldest donation first
        self.assertEqual(rows[1][1], self.child1.user.username)
        self.assertEqual(rows[1][2], self.category2.name)
        self.assertEqual(int(rows[1][3]), 150)
        
        self.assertEqual(int(rows[2][0]), self.donation2.id)  # Next oldest donation
        self.assertEqual(rows[2][1], self.child2.user.username)
        self.assertEqual(rows[2][2], self.category1.name)
        self.assertEqual(int(rows[2][3]), 200)
        
        self.assertEqual(int(rows[3][0]), self.donation1.id)  # Most recent donation
        self.assertEqual(rows[3][1], self.child1.user.username)
        self.assertEqual(rows[3][2], self.category1.name)
        self.assertEqual(int(rows[3][3]), 100)

    def test_export_donations_report_with_date_filter(self):
        """Test export_donations_report with date filtering."""
        # Get report for only recent donations (last 3 days)
        three_days_ago = self.now - timedelta(days=3)
        csv_data = DonationCalculator.export_donations_report(start_date=three_days_ago)
        
        # Parse the CSV
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)
        
        # Should only have 1 donation + header = 2 rows
        self.assertEqual(len(rows), 2)
        
        # Check it contains only the most recent donation
        self.assertEqual(int(rows[1][0]), self.donation1.id)
        self.assertEqual(rows[1][1], self.child1.user.username)
        self.assertEqual(rows[1][2], self.category1.name)
        self.assertEqual(int(rows[1][3]), 100) 