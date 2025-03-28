from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from Volunteen.constants import MAX_PARENT_COINS, PARENT_TOPUP_AMOUNT

from parentApp.models import Parent


class Command(BaseCommand):
    help = "Grant monthly teencoins to parents (up to max). Only once a month."

    def handle(self, *args, **options):
        today = timezone.localtime().date()
        self.stdout.write("#################### grant monthly teencoins ###############")
        # We only do the monthly top-up if it's the first day of the month,
        # but also check parent's last_monthly_topup to avoid re-adding multiple times
        if today.day != 1:
            self.stdout.write("[SKIP] Today is not the 1st of the month. No monthly top-up done.")
            return

        # If you're sure the script only runs once per day, you might skip the top-up date check.
        # But let's do it properly anyway:
        parents = Parent.objects.all()
        count = 0
        for parent in parents:
            # If they've never had a top-up before or haven't had one yet this month...
            if not parent.last_monthly_topup or (
                parent.last_monthly_topup.month != today.month or
                parent.last_monthly_topup.year != today.year
            ):
                children=parent.children.all()
                num_children = children.count()
                if num_children == 0:
                    self.stdout.write(f"[SKIP] Parent '{parent.user.username}' has no children.")
                    continue
                old_balance = parent.available_teencoins
                # Add PARENT_TOPUP_AMOUNT, respecting the max limit
                new_balance = min(MAX_PARENT_COINS*num_children, old_balance + (PARENT_TOPUP_AMOUNT*num_children))
                parent.available_teencoins = new_balance
                parent.last_monthly_topup = today
                parent.save()
                count += 1
                self.stdout.write(
                    f"[OK] Parent '{parent.user.username}' children number: {num_children}, top-up from {old_balance} to {new_balance}. "
                )

        self.stdout.write(f"[DONE] Granted monthly teencoins to {count} parents.")
        self.stdout.write("#################### end grant monthly teencoins ###############")
