from datetime import timedelta, datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from shopApp.models import Shop
from managementApp.models import DonationSpending, DonationCategory
from shopApp.utils.ShopDonationUtils import ShopDonationUtils
from unittest.mock import patch

class TestShopDonationUtils(TestCase):
    def setUp(self):
        # Create a shop user and shop.
        self.user = User.objects.create_user(
            username='shopuser',
            password='password123',
            email='shop@example.com'
        )
        self.shop = Shop.objects.create(
            user=self.user,
            name="Test Shop",
            max_points=1000
        )
        # Create DonationCategory instances.
        self.category_food = DonationCategory.objects.create(name='Food')
        self.category_clothing = DonationCategory.objects.create(name='Clothing')

    @patch('django.utils.timezone.now')
    def test_get_monthly_donation_spending_for_shop(self, mock_now):
        # Define a fixed timestamp.
        fixed_now = timezone.make_aware(datetime(2024, 4, 15, 12, 0, 0))
        mock_now.return_value = fixed_now
        # The start of the month from fixed_now.
        start_of_month = fixed_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Create a spending that will be considered "current month" (auto_now_add will use fixed_now).
        spending_current = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=100,
            note="Current month spending",
            category=self.category_food,
        )
        # Create a spending and then force-update its date to be before the current month.
        spending_old = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=200,
            note="Old spending",
            category=self.category_food,
        )
        # Set spending_old's date to before the start of the month.
        DonationSpending.objects.filter(pk=spending_old.pk).update(date_spent=start_of_month - timedelta(days=1))

        result = ShopDonationUtils.get_monthly_donation_spending_for_shop(self.shop)
        # Expect only the current-month spending of 100 to be counted.
        self.assertEqual(result, 100)

        with self.assertRaises(ValueError):
            ShopDonationUtils.get_monthly_donation_spending_for_shop(None)

    @patch('django.utils.timezone.now')
    def test_get_total_donation_spending_for_shop(self, mock_now):
        fixed_now = timezone.make_aware(datetime(2024, 4, 15, 12, 0, 0))
        mock_now.return_value = fixed_now

        DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=150,
            note="Spending 1",
            category=self.category_food,
        )
        DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=250,
            note="Spending 2",
            category=self.category_clothing,
        )
        result = ShopDonationUtils.get_total_donation_spending_for_shop(self.shop)
        self.assertEqual(result, 400)

        with self.assertRaises(ValueError):
            ShopDonationUtils.get_total_donation_spending_for_shop(None)

    @patch('django.utils.timezone.now')
    def test_get_donation_spending_by_category(self, mock_now):
        fixed_now = timezone.make_aware(datetime(2024, 4, 15, 12, 0, 0))
        mock_now.return_value = fixed_now

        DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=100,
            note="Food spending",
            category=self.category_food,
        )
        DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=200,
            note="Clothing spending",
            category=self.category_clothing,
        )
        DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=50,
            note="More Food spending",
            category=self.category_food,
        )
        result = ShopDonationUtils.get_donation_spending_by_category(self.shop)
        # Expect Food: 150 and Clothing: 200.
        self.assertEqual(result, {"Food": 150, "Clothing": 200})

        with self.assertRaises(ValueError):
            ShopDonationUtils.get_donation_spending_by_category(None)

    @patch('django.utils.timezone.now')
    def test_get_donation_spending_in_date_range(self, mock_now):
        fixed_now = timezone.make_aware(datetime(2024, 4, 15, 12, 0, 0))
        mock_now.return_value = fixed_now
        start_date = fixed_now - timedelta(days=10)
        end_date = fixed_now + timedelta(days=10)

        # Create spending inside the date range.
        spending_inside = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=100,
            note="Inside range",
            category=self.category_food,
        )
        # Create spending that will be forced outside the date range.
        spending_outside = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=200,
            note="Outside range",
            category=self.category_food,
        )
        # Set spending_outside's date to 20 days before fixed_now.
        DonationSpending.objects.filter(pk=spending_outside.pk).update(date_spent=fixed_now - timedelta(days=20))

        result = ShopDonationUtils.get_donation_spending_in_date_range(self.shop, start_date, end_date)
        # Expect only the inside spending (100) to be counted.
        self.assertEqual(result, 100)

        with self.assertRaises(ValueError):
            ShopDonationUtils.get_donation_spending_in_date_range(None, start_date, end_date)

    @patch('django.utils.timezone.now')
    def test_get_all_spendings_for_shop(self, mock_now):
        fixed_now = timezone.make_aware(datetime(2024, 4, 15, 12, 0, 0))
        mock_now.return_value = fixed_now

        spending1 = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=100,
            note="Spending 1",
            category=self.category_food,
        )
        spending2 = DonationSpending.objects.create(
            shop=self.shop,
            amount_spent=200,
            note="Spending 2",
            category=self.category_clothing,
        )
        spendings = ShopDonationUtils.get_all_spendings_for_shop(self.shop)
        self.assertEqual(len(spendings), 2)
        for record in spendings:
            self.assertIn('date_spent', record)
            self.assertIn('note', record)
            self.assertIn('amount_spent', record)
            self.assertIn('category', record)

        limited_spendings = ShopDonationUtils.get_all_spendings_for_shop(self.shop, limit=1)
        self.assertEqual(len(limited_spendings), 1)

        with self.assertRaises(ValueError):
            ShopDonationUtils.get_all_spendings_for_shop(None)
