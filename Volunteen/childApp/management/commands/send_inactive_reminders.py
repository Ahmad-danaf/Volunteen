from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from childApp.models import Child
from teenApp.utils.NotificationManager import NotificationManager

import datetime

class Command(BaseCommand):
    help = 'Send WhatsApp reminders for children inactive for 7+ days (Mon/Thu only)'

    def handle(self, *args, **options):
        # Only run on Monday or Thursday
        today = timezone.localtime().date().weekday()  # Monday = 0, Thursday = 3
        if today not in [0, 3]:
            self.stdout.write(self.style.WARNING("Command only runs on Monday and Thursday."))
            return

        count = self.send_inactive_children_reminders(days_inactive=7)

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No inactive children found!"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully sent reminders for {count} inactive children")
            )

    def send_inactive_children_reminders(self, days_inactive=7):
        cutoff = timezone.now() - timedelta(days=days_inactive)
        inactive_children = []

        for child in Child.objects.select_related("user").all():
            user = child.user

            # Must have active subscription
            if not hasattr(child, "subscription") or not child.subscription.is_active():
                continue

            # Must have personal info with last_activity
            personal_info = getattr(user, "personal_info", None)
            if not personal_info or not personal_info.last_activity:
                continue

            if personal_info.last_activity < cutoff:
                inactive_children.append((child, personal_info.last_activity))

        # Prepare and send WhatsApp message
        if inactive_children:
            message = "🚨 *Inactive Children Reminder* 🚨\n"
            message += f"Children who haven't been active for {days_inactive}+ days:\n\n"

            for i, (child, last_activity) in enumerate(inactive_children, 1):
                phone = getattr(child, "phone_number", None)
                phone_info = f"📱 {phone}" if phone else ""
                message += (
                    f"{i}. 👤 *{child.user.username}*\n"
                    f"   {phone_info}\n"
                    f"   ⏰ Last activity: {last_activity.strftime('%Y-%m-%d %H:%M')}\n\n"
                )

            message += "Please follow up with these children! 🙏"
        else:
            message = "🎉 All children with active subscriptions have been active recently!"

        NotificationManager.sent_to_log_group_whatsapp(message)
        return len(inactive_children)
