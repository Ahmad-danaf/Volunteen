import csv
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from childApp.models import Child
from parentApp.models import ChildSubscription

class Command(BaseCommand):
    help = "Initialize ChildSubscription records from a CSV file with subscription data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help="Path to the CSV file (exported from Google Sheet)"
        )

    def handle(self, *args, **options):
        file_path = options['file']
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        row_count = 0

        self.stdout.write("############# Initializing Child Subscriptions ##############")

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    row_count += 1
                    identifier_raw = row.get('identifier').strip()
                    identifier = identifier_raw.zfill(5)
                    username = row.get('username').strip()
                    payment_method = row.get('payment_method', '').strip().upper()
                    plan = row.get('plan', '').strip().upper()
                    start_date_str = row.get('start_date').strip()
                    end_date_str = row.get('end_date').strip()
                    auto_renew_str = row.get('auto_renew', '').strip().upper()

                    try:
                        child = Child.objects.get(identifier=identifier, user__username=username)
                    except Child.DoesNotExist:
                        self.stderr.write(f"[ERROR] Child with identifier '{identifier}' and username '{username}' not found. Skipping.")
                        error_count += 1
                        continue

                    # Parse date
                    try:
                        start_date = datetime.datetime.strptime(start_date_str, "%m/%d/%Y").date()
                        if end_date_str is not None:
                            end_date = datetime.datetime.strptime(end_date_str, "%m/%d/%Y").date()
                        else:
                            end_date = None
                    except Exception as e:
                        self.stderr.write(f"[ERROR] Invalid start_date '{start_date_str}' or end_date '{end_date_str}' for child '{identifier}' and username '{username}': {e}")
                        error_count += 1
                        continue

                    # Calculate end_date
                    if end_date_str is None:
                        if plan == "MONTHLY":
                            end_date = start_date + datetime.timedelta(days=37)
                        elif plan == "YEARLY":
                            end_date = start_date + datetime.timedelta(days=372)
                        else:
                            self.stderr.write(f"[ERROR] Invalid plan '{plan}' for child '{identifier}' and username '{username}'. Skipping.")
                            error_count += 1
                            continue

                    auto_renew = auto_renew_str in ["TRUE", "YES", "1"]
                    
                    if plan not in ChildSubscription.Plan.values:
                        self.stderr.write(f"[ERROR] Row {row_count}: Invalid plan value '{plan}' for child '{identifier}' and username '{username}'")
                        error_count += 1
                        continue

                    if payment_method not in ChildSubscription.PaymentMethod.values:
                        self.stderr.write(f"[ERROR] Row {row_count}: Invalid payment_method '{payment_method}'")
                        error_count += 1
                        continue

                    try:
                        sub, created = ChildSubscription.objects.update_or_create(
                            child=child,
                            defaults={
                                "payment_method": payment_method,
                                "plan": plan,
                                "start_date": start_date,
                                "end_date": end_date,
                                "auto_renew": auto_renew,
                                "status": ChildSubscription.Status.ACTIVE,
                                "updated_at": timezone.now(),
                                "notes": "Initial subscription created from CSV import-init child subscription management command",
                            }
                        )
                        if created:
                            created_count += 1
                            self.stdout.write(f"[SUC] Created subscription for {identifier} and username '{username}'")
                        else:
                            updated_count += 1
                            self.stdout.write(f"[SUC] Updated subscription for {identifier} and username '{username}'")
                    except Exception as e:
                        self.stderr.write(f"[ERROR] Failed to save subscription for {identifier} and username '{username}': {e}")
                        error_count += 1
                        continue

        except FileNotFoundError:
            self.stderr.write(f"[ERROR] File not found: {file_path}")
            return

        # Final summary
        self.stdout.write("############# Finished initializing subscriptions ##############")
        self.stdout.write(f"[INFO] Total rows processed: {row_count}")
        self.stdout.write(f"[SUC] Created: {created_count}")
        self.stdout.write(f"[SUC] Updated: {updated_count}")
        self.stdout.write(f"[SKIP] Skipped: {skipped_count}")
        self.stdout.write(f"[ERROR] Errors: {error_count}")
