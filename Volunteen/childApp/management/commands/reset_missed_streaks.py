from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from childApp.models import Child,StreakMilestoneAchieved

class Command(BaseCommand):
    help = "Reset child.streak_count to last milestone if child missed more than 3 days"

    def handle(self, *args, **kwargs):
        self.stdout.write("========== START: Resetting Missed Streaks ==========\n")
        today = timezone.localdate()
        grace_days = 3
        cutoff_date = today - timedelta(days=grace_days)

        updated_count = 0
        skipped_count = 0

        for child in Child.objects.all():
            # If no streak date recorded, skip (new user or never clicked)
            if not child.last_streak_date:
                skipped_count += 1
                continue

            # Within grace period — no reset
            if child.last_streak_date >= cutoff_date:
                skipped_count += 1
                continue

            # Get the last milestone
            last_milestone = (
                StreakMilestoneAchieved.objects
                .filter(child=child)
                .order_by('-streak_day')
                .values_list('streak_day', flat=True)
                .first()
            ) or 0

            # Only reset if current streak is higher than milestone
            if child.streak_count > last_milestone:
                self.stdout.write(
                    f"{child.user.username} missed streak — resetting from {child.streak_count} -> {last_milestone}"
                )
                child.streak_count = last_milestone
                child.save(update_fields=["streak_count"])
                updated_count += 1
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f"[SUCC] {updated_count} children had their streak reset."))
        self.stdout.write(self.style.NOTICE(f"[INFO] {skipped_count} children skipped (within grace or no data)."))
        self.stdout.write("========== DONE: Resetting Missed Streaks ==========\n")
