from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class UsernameOrPhoneBackend(ModelBackend):
    """
    Allow login with username or phone number from PersonalInfo.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        normalized = username.strip().replace(" ", "").replace("-", "")

        try:
            user = User.objects.filter(
                Q(username=username) | Q(personal_info__phone_number=normalized)
            ).first()
        except User.DoesNotExist:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
