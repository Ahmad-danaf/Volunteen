from django.contrib.auth.models import User
from django.test import TestCase
from .models import Task, Shop
from .forms import IdentifyChildForm, RedemptionForm

class TaskModelTestCase(TestCase):
    def setUp(self):
        self.task = Task.objects.create(title='Test Task', points=50, deadline='2024-12-31')

    def test_task_creation(self):
        self.assertEqual(self.task.title, 'Test Task')
        self.assertEqual(self.task.points, 50)

class IdentifyChildFormTestCase(TestCase):
    def test_form_valid_data(self):
        form_data = {'identifier': '12345', 'secret_code': 'abc'}
        form = IdentifyChildForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_data(self):
        form_data = {'identifier': '', 'secret_code': 'abc'}
        form = IdentifyChildForm(data=form_data)
        self.assertFalse(form.is_valid())

class RedemptionFormTestCase(TestCase):
    def test_form_valid_data(self):
        form_data = {'points': 10}
        form = RedemptionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_data(self):
        form_data = {'points': -10}
        form = RedemptionForm(data=form_data)
        self.assertFalse(form.is_valid())

class ShopModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='shop_user', password='password123')
        self.shop = Shop.objects.create(user=self.user, name='Test Shop', max_points=1000)

    def test_shop_creation(self):
        self.assertEqual(self.shop.user.username, 'shop_user')
        self.assertEqual(self.shop.name, 'Test Shop')
        self.assertEqual(self.shop.max_points, 1000)
