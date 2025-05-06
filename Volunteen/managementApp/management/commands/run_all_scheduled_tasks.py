from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Run all scheduled maintenance tasks for Volunteen"

    def handle(self, *args, **kwargs):
        scheduled_tasks = [
            ("refund_overdue_tasks", "Refund overdue teencoins"),
            ("grant_monthly_parent_points", "Monthly parent top-up"),
            ("check_subscriptions", "Check child subscriptions and expire overdue subscriptions"),
            ('log_suspicious_events',"Log suspicious events"),
        ]

        self.stdout.write("========== START: Daily Scheduled Tasks ==========\n")

        for command_name, description in scheduled_tasks:
            self.stdout.write(f"--- Running: {description} ({command_name}) ---")
            try:
                call_command(command_name)
                self.stdout.write(f"[SUCCESS] {description}\n")
            except Exception as e:
                self.stderr.write(f"[FAILED] {description} -> {str(e)}\n")

        self.stdout.write("========== DONE: All Tasks Finished ==========\n")
