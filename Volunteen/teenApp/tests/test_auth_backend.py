from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from teenApp.models import PersonalInfo
from Volunteen.auth_backends.username_or_phone import UsernameOrPhoneBackend


class UsernameOrPhoneBackendUnitTest(TestCase):
    """Direct unit tests for the custom authentication backend"""

    def setUp(self):
        self.backend = UsernameOrPhoneBackend()
        self.user = User.objects.create_user(username="unit_user", password="test1234")
        self.personal_info = PersonalInfo.objects.get(user=self.user)
        self.personal_info.phone_number = "0511111111"
        self.personal_info.save()

    def test_authenticate_with_username(self):
        user = self.backend.authenticate(None, username="unit_user", password="test1234")
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

    def test_authenticate_with_phone(self):
        user = self.backend.authenticate(None, username="0511111111", password="test1234")
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

    def test_authenticate_with_wrong_password(self):
        user = self.backend.authenticate(None, username="unit_user", password="wrongpass")
        self.assertIsNone(user)

    def test_authenticate_with_invalid_phone(self):
        user = self.backend.authenticate(None, username="0000000000", password="test1234")
        self.assertIsNone(user)


class UsernameOrPhoneBackendIntegrationTest(TestCase):
    """Integration tests using Django's authenticate() with AUTHENTICATION_BACKENDS"""

    def setUp(self):
        self.user = User.objects.create_user(username="int_user", password="test1234")
        self.personal_info = PersonalInfo.objects.get(user=self.user)
        self.personal_info.phone_number = "0522222222"
        self.personal_info.save()

    def test_login_with_username(self):
        user = authenticate(username="int_user", password="test1234")
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

    def test_login_with_phone_number(self):
        user = authenticate(username="0522222222", password="test1234")
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

    def test_login_with_invalid_phone(self):
        user = authenticate(username="0000000000", password="test1234")
        self.assertIsNone(user)

    def test_login_with_wrong_password(self):
        user = authenticate(username="int_user", password="wrongpass")
        self.assertIsNone(user)
