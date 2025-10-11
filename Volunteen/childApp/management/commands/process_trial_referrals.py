from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from childApp.models import Child, ChildReferral
from teenApp.entities import TaskCompletion
from childApp.utils.ChildRedemptionManager import ChildRedemptionManager
from teenApp.utils.NotificationManager import NotificationManager

REFERRAL_BONUS = 5
REFERRAL_NOTE_TAG = "בונוס חבר מביא חבר"


class Command(BaseCommand):
    help = "Extend trials for temp users who purchased and reward their referrers with a coin bonus."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Run without writing to the database.")
        parser.add_argument(
            "--only-trial",
            action="store_true",
            help="Only process trial extensions (skip referrer bonuses).",
        )
        parser.add_argument(
            "--only-bonus",
            action="store_true",
            help="Only process referrer bonuses (skip trial extensions).",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        only_trial = options.get("only_trial", False)
        only_bonus = options.get("only_bonus", False)

        temp_children = Child.objects.filter(is_temp_user=True)
        total = temp_children.count()
        print("############PROCESS TRIAL REFERRALS############")
        print(f"Scanning {total} temp users…")
        purchased_children = []
        for child in temp_children.iterator():
            try:
                if ChildRedemptionManager.get_all_redemptions(child).exists():
                    purchased_children.append(child)
            except Exception as e:
                print(f"[WARN] Failed to fetch redemptions for Child id={child.id}: {e}")

        print(f"Found {len(purchased_children)} temp users with ≥1 redemption.")

        extended_count = 0
        rewarded_count = 0

        if not only_bonus:
            extended_count = self.process_trial_extensions(purchased_children, dry_run)

        if not only_trial:
            rewarded_count = self.process_referrer_bonuses(purchased_children, dry_run)

        print(
            f"Done. Trial extensions: {extended_count}; Referrer bonuses: {rewarded_count}."
        )
        print("##############END PROCESS TRIAL REFERRALS##############")

    # ========================= TRIAL EXTENSION ========================= #
    def process_trial_extensions(self, children, dry_run: bool) -> int:
        """Extend `trial_end` by +1 calendar month for qualifying temp children."""
        now_date = timezone.localdate()
        extended_count = 0

        for child in children:
            referral = (
                ChildReferral.objects.filter(referred_child=child).order_by("created_at").first()
            )
            if referral is not None:
                if referral.trial_extended_at:
                    continue

                old_trial = child.trial_end or now_date
                new_trial = old_trial + relativedelta(months=1)
                msg = (
                    f"[TRIAL] Child id={child.id}: {old_trial} -> {new_trial} (via referral id={referral.id})"
                )
                if dry_run:
                    print(f"[DRY-RUN] {msg}")
                    continue

                with transaction.atomic():
                    # Lock both rows to avoid races
                    c = Child.objects.select_for_update().get(pk=child.pk)
                    r = ChildReferral.objects.select_for_update().get(pk=referral.pk)
                    c.trial_end = new_trial
                    c.save(update_fields=["trial_end"])  
                    r.trial_extended_at = timezone.now()
                    r.save(update_fields=["trial_extended_at"])  
                print(msg)
                extended_count += 1
                continue

            if child.trial_end and child.trial_end >= now_date + timedelta(days=25):
                continue

            old_trial = child.trial_end or now_date
            new_trial = old_trial + relativedelta(months=1)
            msg = f"[TRIAL] Child id={child.id}: {old_trial} -> {new_trial} (no referral)"
            if dry_run:
                print(f"[DRY-RUN] {msg}")
                continue

            with transaction.atomic():
                c = Child.objects.select_for_update().get(pk=child.pk)
                c.trial_end = new_trial
                c.save(update_fields=["trial_end"]) 
            print(msg)
            extended_count += 1

        return extended_count
    
    
    def _notify_child_of_referral_bonus(self, child):
        """Send a WhatsApp message to the child when their referrer gets a bonus."""
        phone = child.phone_number
        if not phone:
            print(f"[WARN] No phone number for Child id={child.id}, skipping WhatsApp notification.")
            return

        msg = (
            "شكراً من القلب! 🧡\n"
            "انضم متطوّع جديد لعائلة Volunteen بفضلك 🤝\n"
            "أنت السبب بنشر الخير والطاقة الحلوة بالمجتمع 💪🌍\n\n"
            "🎉 وكجائزة إلك: حصلت على 5 TeenCoins 💰🪙\n"
            "استمر بالتأثير الجميل! 🌟🚀"
        )
        sent = NotificationManager.sent_whatsapp(msg, phone)
        if sent:
            print(f"[WHATSAPP] Sent referral bonus message to Child id={child.id} ({phone})")
        else:
            print(f"[WARN] Failed to send WhatsApp to Child id={child.id} ({phone})")

    # ======================= REFERRER BONUSES ========================= #
    def process_referrer_bonuses(self, children, dry_run: bool) -> int:
        rewarded_count = 0
        notified_children = set()
        
        for child in children:
            referral = (
                ChildReferral.objects
                .filter(referred_child=child, referrer__isnull=False)
                .order_by("created_at")
                .first()
            )
            if referral is None:
                continue

            if referral.rewarded_at:
                continue

            referrer = referral.referrer
            tc = (
                TaskCompletion.objects
                .filter(child=referrer, status="approved")
                .order_by("-completion_date", "-id")
                .first()
            )
            if not tc:
                print(
                    f"[SKIP] No approved TaskCompletion for referrer child id={referrer.id}; cannot attach bonus."
                )
                continue

            referred_name = child.user.first_name or ""
            hebrew_note = (
                f"🎁 {REFERRAL_NOTE_TAG}: קיבלת {REFERRAL_BONUS} TeenCoins על הזמנת {referred_name} להצטרף. כל הכבוד!"
            )

            msg = (
                f"[BONUS] Referrer child id={referrer.id}: +{REFERRAL_BONUS} bonus_points/remaining_coins "
                f"(TaskCompletion id={tc.id}; referral id={referral.id})"
            )
            
            if dry_run:
                print(f"[DRY-RUN] {msg}")
                continue

            with transaction.atomic():
                tc_locked = TaskCompletion.objects.select_for_update().get(pk=tc.pk)
                tc_locked.bonus_points = (tc_locked.bonus_points or 0) + REFERRAL_BONUS
                tc_locked.remaining_coins = (tc_locked.remaining_coins or 0) + REFERRAL_BONUS
                if tc_locked.mentor_feedback:
                    tc_locked.mentor_feedback = tc_locked.mentor_feedback.strip() + " & " + hebrew_note
                else:
                    tc_locked.mentor_feedback = hebrew_note
                tc_locked.save(update_fields=["bonus_points", "remaining_coins", "mentor_feedback"])  

                r_locked = ChildReferral.objects.select_for_update().get(pk=referral.pk)
                r_locked.rewarded_at = timezone.now()
                r_locked.reward_amount = REFERRAL_BONUS
                r_locked.save(update_fields=["rewarded_at", "reward_amount"])  

            print(msg)
            rewarded_count += 1
            notified_children.add(referrer.id)

        for child_id in notified_children:
            child = Child.objects.get(pk=child_id)
            self._notify_child_of_referral_bonus(child)

        return rewarded_count
