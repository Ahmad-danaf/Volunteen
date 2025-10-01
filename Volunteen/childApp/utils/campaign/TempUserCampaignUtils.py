import re
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django_q.tasks import async_task  

from childApp.models import Child,ChildReferral
from parentApp.models import ChildSubscription
from managementApp.utils.CampaignManagerUtils import CampaignManagerUtils
from managementApp.utils import UserCreationUtility
from teenApp.utils.NotificationManager import NotificationManager
User = get_user_model()

DEFAULT_TRIAL_DAYS = 7
DEFAULT_CITY_CODE = "TLV"
DEFAULT_MENTOR_CAMPAIGN_GROUP_NAME  = "משתמשים זמניים"
TASK_GROUP_SLUG_FOR_NEW_USERS = "Starter Pack"
DEFAULT_DUPLICATED_DEADLINE_DAYS = 3
WELCOME_NEW_CHILD_MSG = """أهلاً وسهلاً بك يا {name} في عالم Volunteen! 🧡✨
وصلت للمكان الصح ✅
معانا بـVolunteen، الخير إله طعم تاني 😋
بتاخد جوائز 🎁 وهدايا 🎉 على كل عمل طيب 💪
يلاااااا اجمع TeenCoins 💰 وسابق الكل عالخير! 🧡🔥

🏠 صفحتك الشخصية: https://www.volunteen.site/child/home/

📸 تابعونا عالإنستا: https://rb.gy/9i3yxf

👇 انضموا لجروب الواتساب: http://bit.ly/484hQf1
"""

THANKS_REFERRER_MSG = """شكراً من القلب!🧡
تم انضمام {name} لعائلة Volunteen 🤝
كل عمل خيري بعمله ✨ بميزان حسناتك إنت 🙌
أنت بتساعدنا نكبر ونقوّي المجتمع سوا 💪🌍

🎉 وكجائزة لك: حصلت على 5 TeenCoins 💰🪙
استمر بالتأثير الجميل! 🌟🚀
"""


class TempUserCampaignUtils:

    @staticmethod
    def check_full_name(full_name: str) -> tuple[bool, str | None]:
        """
        Ensure full_name contains at least first and last names.
        Returns: (is_ok, heb_msg_if_error)
        """
        if not full_name:
            return False, "נא להזין שם מלא"
        parts = [p for p in full_name.strip().split() if p]
        if len(parts) < 2:
            return False, "נא להזין שם פרטי ושם משפחה"
        return True, None

    @staticmethod
    def check_phone_unique(phone: str) -> tuple[bool, str | None]:
        """
        Phone must not exist for any existing child/user.
        We look up by the known location of phone: user.personal_info.phone_number (if present).
        Returns: (is_ok, heb_msg_if_error)
        """
        if not phone:
            return False, "נא להזין מספר טלפון"

        exists = User.objects.filter(personal_info__phone_number=phone).exists()
        if exists:
            return False, "מספר הטלפון כבר רשום במערכת"
        return True, None
    
    @staticmethod
    def check_password(password: str) -> tuple[bool, str | None]:
        """
        Minimal password validation.
        Returns (is_valid, error_message).
        """
        if not password:
            return False, "נא להזין סיסמה"
        if len(password) < 6:
            return False, "הסיסמה חייבת להכיל לפחות 6 תווים"
        
        return True, None
        

    @staticmethod
    def precheck(full_name: str, phone: str, phone_confirm: str,
                password: str, parent_approval: bool) -> tuple[bool, str|None]:
        """
        Run all checks and return first blocking error (for smooth UX).
        """
        ok, msg = TempUserCampaignUtils.check_full_name(full_name)
        if not ok:
            return ok, msg
        
        if not phone_confirm or phone != phone_confirm:
            return False, "מספרי הטלפון אינם תואמים"
        ok, msg = TempUserCampaignUtils.check_phone_unique(phone)
        if not ok:
            return ok, msg
        
        if not parent_approval:
            return False, "יש לאשר את הסכמת ההורים כדי להמשיך"
        
        ok, msg = TempUserCampaignUtils.check_password(password)
        if not ok:
            return ok, msg
        
        return True, None

    @staticmethod
    @transaction.atomic
    def register_and_login(request, full_name: str, phone: str,
                        phone_confirm: str, password: str,
                        parent_approval: bool, ref_child_identifier=None,
                        trial_days: int = DEFAULT_TRIAL_DAYS):
        ok, msg = TempUserCampaignUtils.precheck(full_name, phone, phone_confirm,
                                                password, parent_approval)
        if not ok:
            return None, msg

        username = TempUserCampaignUtils._generate_username_from_name(full_name)
        user = User.objects.create_user(username=username, password=password)
        TempUserCampaignUtils._set_user_name(user, full_name)
        TempUserCampaignUtils._set_user_phone(user, phone)

        identifier = UserCreationUtility.get_next_free_identifier()
        secret_code = UserCreationUtility.generate_secret_code()
        child = Child.objects.create(
            user=user,
            identifier=identifier,
            secret_code=secret_code,
            is_temp_user=True,
            trial_end=timezone.now().date() + timedelta(days=trial_days),
            city=DEFAULT_CITY_CODE,  # default TLV
        )
        TempUserCampaignUtils._ensure_trial_subscription(child)

        mentor = CampaignManagerUtils.get_campaign_mentor()
        institution = CampaignManagerUtils.get_campaign_institution()
        child.mentors.add(mentor)
        child.institution = institution
        child.save()
        TempUserCampaignUtils._add_child_to_mentor_group(child, mentor)
        
        try:
            if ref_child_identifier:
                referrer = Child.objects.filter(identifier=ref_child_identifier).first()
                if referrer:
                    ChildReferral.objects.create(
                        referred_child=child,
                        referrer=referrer
                    )
                    first_name = referrer.user.username.split("_")[0]
                    NotificationManager.sent_whatsapp(THANKS_REFERRER_MSG.format(name=first_name), referrer.user.personal_info.phone_number)
        except Exception as e:
            pass

        if request is not None:
            login(request, user)
        NotificationManager.sent_whatsapp(WELCOME_NEW_CHILD_MSG.format(name=user.first_name), phone)
        TempUserCampaignUtils.enqueue_assign_live_tasks(child.id,mentor.user.id)
        return child, None

    # ---------- Internals ----------

    @staticmethod
    def _generate_username_from_name(full_name: str) -> str:
        """
        Build a unique username:
        - Keeps Hebrew/Arabic letters intact.
        - Base: first_last (Unicode allowed).
        - Adds counter (1,2,3..) if taken.
        """
        parts = [p for p in full_name.strip().split() if p]
        first = parts[0]
        last = " ".join(parts[1:])

        # Keep only letters, numbers, and underscores but allow Unicode letters
        def clean(text: str) -> str:
            # allow any unicode word character and spaces -> replace spaces with underscore
            text = re.sub(r"\s+", "_", text.strip())
            # remove anything that's not unicode word char or underscore
            return re.sub(r"[^\w_]", "", text)

        base = f"{clean(first)}_{clean(last)}".strip("_")
        if not base:
            base = "user"
        base = base[:40]
        
        candidate = base
        i = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{i}"
            i += 1
        return candidate
    
    @staticmethod
    def _set_user_name(user, full_name: str) -> None:
        parts = [p for p in full_name.strip().split() if p]
        first = parts[0]
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        if hasattr(user, "first_name"):
            user.first_name = first
        if hasattr(user, "last_name"):
            user.last_name = last
        user.save(update_fields=["first_name", "last_name"])

    @staticmethod
    def _set_user_phone(user, phone: str) -> None:
        """
        Store phone on user's PersonalInfo if available. Silently no-op if not.
        """
        personal_info = getattr(user, "personal_info", None)
        if personal_info and hasattr(personal_info, "phone_number"):
            personal_info.phone_number = phone
            personal_info.save(update_fields=["phone_number"])
            
    
    @staticmethod
    def _add_child_to_mentor_group(child,mentor):
        """
        Adds the child to the default mentor campaign group.
        """
        if not child or not DEFAULT_MENTOR_CAMPAIGN_GROUP_NAME:
            return
        try:
            from mentorApp.models import MentorGroup
            mentor_group = MentorGroup.objects.filter(
                name=DEFAULT_MENTOR_CAMPAIGN_GROUP_NAME,
                mentor=mentor,
            ).first()
            if mentor_group:
                mentor_group.children.add(child)
        except Exception as e:
            pass
        
    @staticmethod
    def _ensure_trial_subscription(child: Child, days: int = DEFAULT_TRIAL_DAYS, note: str = "Temp trial (campaign)"):
        """
        Create or refresh a non-renewing ACTIVE trial subscription for the child.
        - start_date = today
        - end_date   = today + days
        - plan=MONTHLY, payment=CASH, auto_renew=False
        """
        today = timezone.now().date()
        end = today + timedelta(days=days)

        sub = getattr(child, "subscription", None)
        if sub is None:
            ChildSubscription.objects.create(
                child=child,
                status=ChildSubscription.Status.ACTIVE,
                plan=ChildSubscription.Plan.MONTHLY,
                payment_method=ChildSubscription.PaymentMethod.CASH,
                auto_renew=False,
                start_date=today,
                end_date=end,
                notes=note,
            )
        else:
            sub.status = ChildSubscription.Status.ACTIVE
            sub.plan = ChildSubscription.Plan.MONTHLY
            sub.payment_method = ChildSubscription.PaymentMethod.CASH
            sub.auto_renew = False
            sub.start_date = today
            sub.end_date = end
            if note:
                sub.notes = (sub.notes + "\n" + note) if sub.notes else note
            sub.canceled_at = None
            sub.save(update_fields=[
                "status", "plan", "payment_method", "auto_renew",
                "start_date", "end_date", "notes", "canceled_at",
                "updated_at",
            ])
            
            
    @staticmethod
    def enqueue_assign_live_tasks(child_id: int, assigned_by_id: int | None = None):
        """
        Enqueue an async job to attach all live tasks to a new child.
        """
        try:
            async_task("childApp.utils.campaign.TempUserCampaignUtils.TempUserCampaignUtils._assign_live_tasks", child_id, assigned_by_id)
        except Exception as e:
            pass

    @staticmethod
    def _assign_live_tasks(child_id: int, assigned_by_id: int | None = None):
        """
        Background job: assign all live (not expired) tasks to the given child.
        """
        from teenApp.entities import Task, TaskAssignment
        try:
            child = Child.objects.get(id=child_id)
        except Child.DoesNotExist:
            return

        assigned_by = None
        if assigned_by_id:
            try:
                assigned_by = User.objects.get(id=assigned_by_id)
            except User.DoesNotExist:
                pass

        today = timezone.now().date()
        live_tasks = Task.objects.filter(deadline__gte=today)

        for task in live_tasks:
            if not task.assigned_children.filter(id=child.id).exists():
                task.assigned_children.add(child)
                
            TaskAssignment.objects.get_or_create(
                task=task,
                child=child,
                defaults={"assigned_by": assigned_by},
            )


