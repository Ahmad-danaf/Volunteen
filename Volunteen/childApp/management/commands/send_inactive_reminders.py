from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from childApp.models import Child
from teenApp.utils.NotificationManager import NotificationManager

class Command(BaseCommand):
    help = 'Send WhatsApp reminders for children inactive for 7+ days'

    def handle(self, *args, **options):
        days_inactive = 7 
        
        count = self.send_inactive_children_reminders(days_inactive=days_inactive)
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No inactive children found!"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully sent reminders for {count} inactive children"
                )
            )
            
    def send_inactive_children_reminders(self,days_inactive=7):
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days_inactive)
        
        # Find inactive children with active subscriptions
        inactive_children = []
        for child in Child.objects.all():
            # Check if child has an active subscription
            if hasattr(child, "subscription") and child.subscription.is_active():
                # Check if never logged in or last login older than cutoff
                last_login = child.user.last_login
                if not last_login or last_login < cutoff_date:
                    inactive_children.append(child)
        
        # Prepare the WhatsApp message
        if inactive_children:
            message = "🚨 *Inactive Children Reminder* 🚨\n"
            message += f"Children who haven't logged in for {days_inactive} days:\n\n"
            
            for i, child in enumerate(inactive_children, 1):
                phone_info = f"📱 {child.phone_number}" if child.phone_number else ""
                message += (
                    f"{i}. 👤 *{child.user.username}*\n"
                    f"   {phone_info}\n"
                    f"   ⏰ Last login: {child.user.last_login or 'Never'}\n\n"
                )
            
            message += "Please follow up with these children! 🙏"
        else:
            message = "🎉 Great news! All children with active subscriptions have logged in recently!"
        
        # Send the message
        NotificationManager.sent_to_log_group_whatsapp(message)
        return len(inactive_children)