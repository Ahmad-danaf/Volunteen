
class PersonalInfoUtils:
    @staticmethod
    def validate_phone(phone: str) -> bool:
        return phone.isdigit() and phone.startswith('0') and len(phone) == 10

    @staticmethod
    def update_user_phone(user, phone: str) -> bool:
        if not PersonalInfoUtils.validate_phone(phone):
            return False
        personal_info = getattr(user, 'personal_info', None)
        if not personal_info:
            from teenApp.models import PersonalInfo
            personal_info = PersonalInfo.objects.create(user=user)
        personal_info.phone_number = phone
        personal_info.save()
        return True
