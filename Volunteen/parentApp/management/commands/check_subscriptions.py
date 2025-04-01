from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from parentApp.models import ChildSubscription  # Adjust the import to match your project structure

class Command(BaseCommand):
    help = (
        "Automatically expire past-due subscriptions, auto-renew credit-card subscriptions, "
        "and send 7-day expiration warnings."
    )

    def handle(self, *args, **options):
        self.stdout.write("############# check child subscriptions ##############")
        today = timezone.now().date()

        expired_count = 0
        auto_renew_count = 0

        # Expire overdue subscriptions (status ACTIVE with end_date before today)
        expired_subs = ChildSubscription.objects.filter(
            status=ChildSubscription.Status.ACTIVE,
            end_date__lt=today
        )
        for sub in expired_subs:
            try:
                sub.expire()
                expired_count += 1
                self.stdout.write(
                    f"[SUC] Expired subscription (ID: {sub.id}) for child {sub.child.identifier} &USERNAME: {sub.child.user.username}."
                )
            except Exception as e:
                self.stderr.write(
                    f"[ERROR] Failed to expire subscription (ID: {sub.id}) for child {sub.child.identifier} &USERNAME: {sub.child.user.username}: {e}"
                )

        # Auto-renew subscriptions with credit card payments, auto_renew=True, and end_date <= today.
        auto_renew_subs = ChildSubscription.objects.filter(
            status=ChildSubscription.Status.ACTIVE,
            payment_method=ChildSubscription.PaymentMethod.CREDIT,
            auto_renew=True,
            end_date__lte=today,
        )
        for sub in auto_renew_subs:
            try:
                if sub.plan == ChildSubscription.Plan.MONTHLY:
                    new_end = sub.end_date + timedelta(days=37)
                elif sub.plan == ChildSubscription.Plan.YEARLY:
                    new_end = sub.end_date + timedelta(days=372)
                else:
                    self.stderr.write(
                        f"[ERROR] Unknown plan type for subscription (ID: {sub.id})."
                    )
                    continue

                sub.end_date = new_end
                sub.save()
                auto_renew_count += 1
                self.stdout.write(
                    f"[SUC] Auto-renewed subscription (ID: {sub.id}) for child {sub.child.identifier} &USERNAME: {sub.child.user.username}. New end date: {sub.end_date}."
                )
            except Exception as e:
                self.stderr.write(
                    f"[ERROR] Failed to auto-renew subscription (ID: {sub.id}) for child {sub.child.identifier} &USERNAME: {sub.child.user.username}: {e}"
                )

        # Send (or log) 7-day expiration warnings
        # warning_count = 0
        #warning_date = today + timedelta(days=7)
        #warning_subs = ChildSubscription.objects.filter(
        #    status=ChildSubscription.Status.ACTIVE,
        #    end_date=warning_date
        #)
        #for sub in warning_subs:
        #    try:
        #        # Here, instead of sending an email/SMS, we log the warning.
        #        self.stdout.write(
        #            f"[SUC] 7-day warning: Subscription (ID: {sub.id}) for child {sub.child.identifier} expires in 7 days."
        #        )
        #        warning_count += 1
        #    except Exception as e:
        #        self.stderr.write(
        #            f"[ERROR] Failed to log warning for subscription (ID: {sub.id}): {e}"
        #        )

        # Final summary log
        self.stdout.write("############# Finished checking subscriptions ##############")
        self.stdout.write(f"[SUC] Total expired subscriptions: {expired_count}")
        self.stdout.write(f"[SUC] Total auto-renewed subscriptions: {auto_renew_count}")
        #self.stdout.write(f"[SUC] Total 7-day warnings sent: {warning_count}")
