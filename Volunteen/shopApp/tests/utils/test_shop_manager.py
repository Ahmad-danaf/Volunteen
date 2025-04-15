import json
from datetime import timedelta, datetime
import random
from unittest.mock import patch, MagicMock, ANY

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from shopApp.utils.shop_manager import ShopManager
from shopApp.models import Shop, Reward, Redemption, RedemptionRequest, Category
from childApp.models import Child
from childApp.utils.TeenCoinManager import TeenCoinManager
from teenApp.utils.NotificationManager import NotificationManager
from Volunteen.constants import MAX_REWARDS_PER_DAY, REDEMPTION_REQUEST_EXPIRATION_MINUTES, MAX_SHOPS_PER_DAY
from shopApp.utils.ShopDonationUtils import ShopDonationUtils


class TestShopManager(TestCase):
    """Test cases for the ShopManager utility class."""

    def setUp(self):
        """Set up test data before each test method."""
        # Create users
        self.shop_user = User.objects.create_user(
            username='testshop',
            password='password123',
            email='testshop@example.com',
            first_name='Test',
            last_name='Shop'
        )
        
        self.child_user = User.objects.create_user(
            username='testchild',
            password='password123',
            email='testchild@example.com',
            first_name='Test',
            last_name='Child'
        )
        
        # Create shop
        self.shop = Shop.objects.create(
            user=self.shop_user,
            name='Test Shop',
            max_points=1000
        )
        
        # Create category
        self.category = Category.objects.create(
            code='food',
            name='Food'
        )
        
        # Add category to shop
        self.shop.categories.add(self.category)
        
        # Create child with required identifier field
        self.child = Child.objects.create(
            user=self.child_user,
            identifier='12345',
            secret_code='123'
        )
        
        # Create rewards
        self.reward1 = Reward.objects.create(
            title='Test Reward 1',
            description='Test Reward 1 Description',
            points_required=100,
            shop=self.shop,
            is_visible=True
        )
        
        self.reward2 = Reward.objects.create(
            title='Test Reward 2',
            description='Test Reward 2 Description',
            points_required=200,
            shop=self.shop,
            is_visible=True
        )
        
        self.reward3 = Reward.objects.create(
            title='Hidden Reward',
            description='Hidden Reward Description',
            points_required=300,
            shop=self.shop,
            is_visible=False
        )

    def test_get_random_digits(self):
        """Test that get_random_digits returns the correct length string of digits."""
        # Test with default parameter (3 digits)
        result = ShopManager.get_random_digits()
        self.assertEqual(len(result), 3)
        self.assertTrue(result.isdigit())
        
        # Test with specified length
        result = ShopManager.get_random_digits(5)
        self.assertEqual(len(result), 5)
        self.assertTrue(result.isdigit())

    def test_get_all_shop_rewards(self):
        """Test that get_all_shop_rewards returns all rewards for a shop."""
        rewards = ShopManager.get_all_shop_rewards(self.shop.id)
        self.assertEqual(rewards.count(), 3)  # Should return all 3 rewards
        self.assertIn(self.reward1, rewards)
        self.assertIn(self.reward2, rewards)
        self.assertIn(self.reward3, rewards)

    def test_get_all_visible_rewards(self):
        """Test that get_all_visible_rewards returns only visible rewards."""
        rewards = ShopManager.get_all_visible_rewards(self.shop.id)
        self.assertEqual(rewards.count(), 2)  # Should return only visible rewards
        self.assertIn(self.reward1, rewards)
        self.assertIn(self.reward2, rewards)
        self.assertNotIn(self.reward3, rewards)  # Hidden reward should not be included

    @patch('shopApp.utils.ShopDonationUtils.ShopDonationUtils.get_monthly_donation_spending_for_shop')
    @patch('django.db.models.QuerySet.filter')
    def test_get_points_used_this_month(self, mock_filter, mock_donation_spending):
        """Test that get_points_used_this_month returns the correct sum."""
        # Mock the donation spending
        mock_donation_spending.return_value = 0
        
        # Create a mock QuerySet and mock the filter method
        current_month_mock = MagicMock()
        current_month_mock.aggregate.return_value = {'total_points': 300}
        mock_filter.return_value = current_month_mock
        
        # Test the method with mocked QuerySet filtering
        points_used = ShopManager.get_points_used_this_month(self.shop)
        self.assertEqual(points_used, 300)  # Only current month
        
        # Verify the correct filter was applied
        mock_filter.assert_called_once_with(shop=self.shop, date_redeemed__gte=ANY)

    def test_get_remaining_points_this_month(self):
        """Test that get_remaining_points_this_month returns correct remaining points."""
        # Create some redemptions for this month
        current_time = timezone.now()
        
        Redemption.objects.create(
            child=self.child,
            reward=self.reward1,
            points_used=100,
            shop=self.shop,
            quantity=1,
            date_redeemed=current_time
        )
        
        # Set locked points
        self.shop.locked_usage_this_month = 200
        self.shop.save()
        
        # Test the method with mocked 'now'
        with patch('shopApp.utils.shop_manager.now') as mock_now:
            # Also mock ShopDonationUtils
            with patch('shopApp.utils.ShopDonationUtils.ShopDonationUtils.get_monthly_donation_spending_for_shop', return_value=0):
                mock_now.return_value = current_time
                remaining_points = ShopManager.get_remaining_points_this_month(self.shop)
                expected_remaining = self.shop.max_points - 100 - 200  # max - used - locked
                self.assertEqual(remaining_points, expected_remaining)
        
    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.redeem_teencoins')
    @patch('teenApp.utils.NotificationManager.NotificationManager.sent_mail')
    @patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month')
    @patch('shopApp.utils.shop_manager.localdate')
    @patch('shopApp.utils.shop_manager.get_object_or_404')
    @patch('shopApp.utils.shop_manager.Redemption.objects.filter')
    def test_redeem_teencoins_for_rewards_success(
        self,
        mock_filter,
        mock_get_object,
        mock_localdate,
        mock_remaining_points,
        mock_sent_mail,
        mock_redeem_teencoins,
        mock_get_total_active_teencoins
    ):
        """Test successful redemption of TeenCoins for rewards."""
        # Set up the current date
        mock_date = timezone.now().date()
        mock_localdate.return_value = mock_date

        # Ensure the child has enough TeenCoins
        mock_get_total_active_teencoins.return_value = 500  
        mock_redeem_teencoins.return_value = None  # Redeem method completes without error

        # Make sure the shop has sufficient remaining points
        mock_remaining_points.return_value = 1000

        # When get_object_or_404 is called, return the test reward
        mock_get_object.return_value = self.reward1

        # Patch Redemption.objects.filter to simulate no redemptions done today
        mock_qs = MagicMock()
        mock_qs.count.return_value = 0
        mock_qs.aggregate.return_value = {'total_points': 0}
        mock_filter.return_value = mock_qs

        # Set up selected rewards with just one reward (100 points)
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]

        # Patch the shop's unlock_monthly_points method to avoid the actual DB save
        with patch.object(self.shop, 'unlock_monthly_points') as mock_unlock:
            result = ShopManager.redeem_teencoins_for_rewards(self.child, self.shop, selected_rewards)
            # Verify that the unlock method was called with the expected points
            mock_unlock.assert_called_once_with(100)

        # Check the returned result
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['points_used'], 100)
        self.assertEqual(len(result['redemptions']), 1)

        # Verify that the TeenCoin redemption happened correctly
        mock_redeem_teencoins.assert_called_once_with(self.child, 100)

        # Check that a notification was sent
        self.assertGreaterEqual(mock_sent_mail.call_count, 1)


    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    def test_redeem_teencoins_for_rewards_not_enough_points(self, mock_get_total_active_teencoins):
        """Test redemption failure when child doesn't have enough TeenCoins."""
        # Mock the TeenCoin method to return insufficient points
        mock_get_total_active_teencoins.return_value = 50  # Not enough TeenCoins
        
        # Set up selected rewards
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]
        
        result = ShopManager.redeem_teencoins_for_rewards(self.child, self.shop, selected_rewards)
        
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'אין מספיק נקודות ברשותך.')
        
        # Check that no Redemption objects were created
        redemptions = Redemption.objects.filter(child=self.child)
        self.assertEqual(redemptions.count(), 0)

    def test_redeem_teencoins_for_rewards_exceed_daily_limit(self):
        """Test redemption failure when exceeding the daily limit."""
        current_time = timezone.now()
        current_date = current_time.date()
        
        # Create redemptions to reach the daily limit
        for i in range(MAX_REWARDS_PER_DAY):
            Redemption.objects.create(
                child=self.child,
                reward=self.reward1,
                points_used=self.reward1.points_required,
                shop=self.shop,
                quantity=1,
                date_redeemed=current_time
            )
        
        # Set up selected rewards
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]
        
        # Mock the localdate function to return our fixed date
        with patch('shopApp.utils.shop_manager.localdate') as mock_localdate:
            mock_localdate.return_value = current_date
            
            result = ShopManager.redeem_teencoins_for_rewards(self.child, self.shop, selected_rewards)
            
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['message'], 'הילד הגיע למגבלת הנקודות היומית של החנות.')

    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    def test_can_redeem_rewards_success(self, mock_get_total_active_teencoins):
        """Test that can_redeem_rewards returns success for a valid redemption request."""
        # Mock the TeenCoin method
        mock_get_total_active_teencoins.return_value = 500  # Child has enough TeenCoins
        
        # Set up selected rewards
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]
        
        # Mock ShopManager.get_remaining_points_this_month to return sufficient points
        with patch('shopApp.utils.shop_manager.ShopManager.get_remaining_points_this_month', return_value=1000):
            result = ShopManager.can_redeem_rewards(self.child, self.shop, selected_rewards)
            
            self.assertEqual(result['status'], 'success')

    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    def test_can_redeem_rewards_exceed_daily_limit(self, mock_get_total_active_teencoins):
        """Test can_redeem_rewards with daily limit exceeded."""
        # Mock the TeenCoin method
        mock_get_total_active_teencoins.return_value = 500  # Child has enough TeenCoins
        
        current_time = timezone.now()
        current_date = current_time.date()
        
        # Create redemptions to reach the daily limit
        for i in range(MAX_REWARDS_PER_DAY):
            Redemption.objects.create(
                child=self.child,
                reward=self.reward1,
                points_used=self.reward1.points_required,
                shop=self.shop,
                quantity=1,
                date_redeemed=current_time
            )
        
        # Set up selected rewards
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]
        
        # Mock the localdate function to return our fixed date
        with patch('shopApp.utils.shop_manager.localdate') as mock_localdate:
            mock_localdate.return_value = current_date
            
            result = ShopManager.can_redeem_rewards(self.child, self.shop, selected_rewards, is_approval=False)
            
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['message'], 'הילד הגיע למגבלות הרכישות היומיות.')

    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    def test_can_redeem_rewards_exceed_shop_limit(self, mock_get_total_active_teencoins):
        """Test can_redeem_rewards with shop limit exceeded."""
        # Mock the TeenCoin method
        mock_get_total_active_teencoins.return_value = 500  # Child has enough TeenCoins
        
        current_time = timezone.now()
        current_date = current_time.date()
        
        # Create redemptions for MAX_SHOPS_PER_DAY different shops
        for i in range(MAX_SHOPS_PER_DAY):
            # Create a new shop for each redemption
            shop_user = User.objects.create_user(
                username=f'testshop{i}',
                password='password123'
            )
            
            shop = Shop.objects.create(
                user=shop_user,
                name=f'Test Shop {i}',
                max_points=1000
            )
            
            Redemption.objects.create(
                child=self.child,
                reward=self.reward1,
                points_used=self.reward1.points_required,
                shop=shop,
                quantity=1,
                date_redeemed=current_time
            )
        
        # Create a new shop for our test
        new_shop_user = User.objects.create_user(
            username='newshop',
            password='password123'
        )
        
        new_shop = Shop.objects.create(
            user=new_shop_user,
            name='New Shop',
            max_points=1000
        )
        
        # Set up selected rewards
        selected_rewards = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required
            }
        ]
        
        # Mock the localdate function to return our fixed date
        with patch('shopApp.utils.shop_manager.localdate') as mock_localdate:
            mock_localdate.return_value = current_date
            
            result = ShopManager.can_redeem_rewards(self.child, new_shop, selected_rewards)
            
            self.assertEqual(result['status'], 'error')
            self.assertIn('מגבלת מספר החנויות היומיות', result['message'])

    @patch('teenApp.utils.NotificationManager.NotificationManager.sent_mail')  
    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.redeem_teencoins')
    @patch('childApp.utils.TeenCoinManager.TeenCoinManager.get_total_active_teencoins')
    def test_approve_redemption_requests_success(self, mock_get_total_active_teencoins, mock_redeem_teencoins, mock_sent_mail):
        """Test successful approval of redemption requests."""
        # Mock the TeenCoin methods
        mock_get_total_active_teencoins.return_value = 500  # Child has enough TeenCoins
        mock_redeem_teencoins.return_value = None  # No error
        
        # Set up selected requests
        selected_requests = [
            {
                'reward_id': self.reward1.id,
                'quantity': 1,
                'points': self.reward1.points_required,
                'request_id': 1  # Doesn't matter for this test
            }
        ]
        
        result = ShopManager.approve_redemption_requests(self.child, selected_requests, self.shop)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['points_used'], 100)
        self.assertEqual(len(result['redemptions']), 1)
        
        # Check that TeenCoins were deducted
        mock_redeem_teencoins.assert_called_once_with(self.child, 100)
        
        # Check that Redemption objects were created
        redemptions = Redemption.objects.filter(child=self.child)
        self.assertEqual(redemptions.count(), 1)

    def test_reject_redemption_requests(self):
        """Test rejecting redemption requests."""
        # Create some pending requests
        request1 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward1,
            quantity=1,
            points_used=self.reward1.points_required,
            status='pending',
            locked_points=self.reward1.points_required,
            locked_at=timezone.now()
        )
        
        request2 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward2,
            quantity=1,
            points_used=self.reward2.points_required,
            status='pending',
            locked_points=self.reward2.points_required,
            locked_at=timezone.now()
        )
        
        # Manually increase locked points to match the locked_points in requests
        self.shop.locked_usage_this_month = self.reward1.points_required + self.reward2.points_required
        self.shop.save()
        
        # Store initial locked points
        initial_locked_points = self.shop.locked_usage_this_month
        
        result = ShopManager.reject_redemption_requests([request1, request2])
        
        self.assertEqual(result['status'], 'success')
        
        # Refresh the objects from the database
        request1.refresh_from_db()
        request2.refresh_from_db()
        self.shop.refresh_from_db()
        
        # Check that the requests were marked as rejected
        self.assertEqual(request1.status, 'rejected')
        self.assertEqual(request2.status, 'rejected')
        
        # Check that the locked points were released
        expected_points_released = self.reward1.points_required + self.reward2.points_required
        self.assertEqual(self.shop.locked_usage_this_month, initial_locked_points - expected_points_released)

    def test_expire_old_requests(self):
        """Test expiring old redemption requests."""
        current_time = timezone.now()
        old_time = current_time - timedelta(minutes=REDEMPTION_REQUEST_EXPIRATION_MINUTES + 5)
        
        # Create some old pending requests
        request1 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward1,
            quantity=1,
            points_used=self.reward1.points_required,
            status='pending',
            locked_points=self.reward1.points_required,
            locked_at=old_time
        )
        
        request2 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward2,
            quantity=1,
            points_used=self.reward2.points_required,
            status='pending',
            locked_points=self.reward2.points_required,
            locked_at=old_time
        )
        
        # Create a recent request that shouldn't expire
        recent_request = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward1,
            quantity=1,
            points_used=self.reward1.points_required,
            status='pending',
            locked_points=self.reward1.points_required,
            locked_at=current_time
        )
        
        # Manually set the shop's locked points
        total_locked_points = self.reward1.points_required * 2 + self.reward2.points_required
        self.shop.locked_usage_this_month = total_locked_points
        self.shop.save()
        
        # Store initial locked points
        initial_locked_points = self.shop.locked_usage_this_month
        
        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = current_time
            expired_count = ShopManager.expire_old_requests()
        
        self.assertEqual(expired_count, 2)  # Only the two old requests should expire
        
        # Refresh the objects from the database
        request1.refresh_from_db()
        request2.refresh_from_db()
        recent_request.refresh_from_db()
        self.shop.refresh_from_db()
        
        # Check that the old requests were marked as expired
        self.assertEqual(request1.status, 'expired')
        self.assertEqual(request2.status, 'expired')
        
        # Check that the recent request remained pending
        self.assertEqual(recent_request.status, 'pending')
        
        # Check that the locked points were released for expired requests
        expected_points_released = self.reward1.points_required + self.reward2.points_required
        self.assertEqual(self.shop.locked_usage_this_month, initial_locked_points - expected_points_released)

    @patch('shopApp.utils.shop_manager.ShopManager.approve_redemption_requests')
    @patch('shopApp.utils.shop_manager.ShopManager.can_redeem_rewards')
    def test_approve_multiple_children_success(self, mock_can_redeem, mock_approve_redemption):
        """Test approving redemption requests for multiple children."""
        # Set up child2
        child2_user = User.objects.create_user(
            username='testchild2',
            password='password123'
        )
        child2 = Child.objects.create(
            user=child2_user,
            identifier='67890',  # Unique identifier
            secret_code='456'
        )
        
        # Create pending requests for both children
        request1 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward1,
            quantity=1,
            points_used=self.reward1.points_required,
            status='pending',
            locked_points=self.reward1.points_required,
            locked_at=timezone.now()
        )
        
        request2 = RedemptionRequest.objects.create(
            child=child2,
            shop=self.shop,
            reward=self.reward2,
            quantity=1,
            points_used=self.reward2.points_required,
            status='pending',
            locked_points=self.reward2.points_required,
            locked_at=timezone.now()
        )
        
        # Mock the validation and approval methods
        mock_can_redeem.return_value = {"status": "success", "message": "הבקשה תקפה וניתן לבצע מימוש."}
        mock_approve_redemption.return_value = {"status": "success", "points_used": 100, "redemptions": []}
        
        result = ShopManager.approve_multiple_children(self.shop, RedemptionRequest.objects.filter(status='pending'))
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['results']), 2)  # Should have results for both children
        
        # Check that both requests were processed
        for child_result in result['results']:
            self.assertEqual(child_result['status'], 'success')
            
        # Refresh the objects from the database
        request1.refresh_from_db()
        request2.refresh_from_db()
        
        # Check that the requests were marked as approved
        self.assertEqual(request1.status, 'approved')
        self.assertEqual(request2.status, 'approved')

    @patch('shopApp.utils.shop_manager.ShopManager.approve_redemption_requests')
    @patch('shopApp.utils.shop_manager.ShopManager.can_redeem_rewards')
    def test_approve_multiple_children_partial_success(self, mock_can_redeem, mock_approve_redemption):
        """Test approving redemption requests with partial success."""
        # Set up child2
        child2_user = User.objects.create_user(
            username='testchild2',
            password='password123'
        )
        child2 = Child.objects.create(
            user=child2_user,
            identifier='54321',  # Unique identifier
            secret_code='789'
        )
        
        # Create pending requests for both children
        request1 = RedemptionRequest.objects.create(
            child=self.child,
            shop=self.shop,
            reward=self.reward1,
            quantity=1,
            points_used=self.reward1.points_required,
            status='pending',
            locked_points=self.reward1.points_required,
            locked_at=timezone.now()
        )
        
        request2 = RedemptionRequest.objects.create(
            child=child2,
            shop=self.shop,
            reward=self.reward2,
            quantity=1,
            points_used=self.reward2.points_required,
            status='pending',
            locked_points=self.reward2.points_required,
            locked_at=timezone.now()
        )
        
        # Mock the validation and approval methods
        # First child succeeds, second child fails
        def mock_can_redeem_side_effect(child, shop, selected_requests, is_approval=False):
            if child.id == self.child.id:
                return {"status": "success", "message": "הבקשה תקפה וניתן לבצע מימוש."}
            else:
                return {"status": "error", "message": "אין מספיק נקודות לילד."}
        
        mock_can_redeem.side_effect = mock_can_redeem_side_effect
        mock_approve_redemption.return_value = {"status": "success", "points_used": 100, "redemptions": []}
        
        result = ShopManager.approve_multiple_children(self.shop, RedemptionRequest.objects.filter(status='pending'))
        
        self.assertEqual(result['status'], 'partial_success')
        self.assertEqual(len(result['results']), 2)
        
        # Check individual results
        child1_result = next(r for r in result['results'] if r['child_id'] == self.child.id)
        child2_result = next(r for r in result['results'] if r['child_id'] == child2.id)
        
        self.assertEqual(child1_result['status'], 'success')
        self.assertEqual(child2_result['status'], 'error')
        
        # Refresh the objects from the database
        request1.refresh_from_db()
        request2.refresh_from_db()
        
        # Check that the requests were marked appropriately
        self.assertEqual(request1.status, 'approved')
        self.assertEqual(request2.status, 'pending')  # Should remain pending since it failed
