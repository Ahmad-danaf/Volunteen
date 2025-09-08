import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from shopApp.models import Shop


class Command(BaseCommand):
    help = "Backfill and deduplicate Shop.public_id values."

    def handle(self, *args, **options):
        self.stdout.write("Starting backfill of Shop.public_id...")

        # Step 1: Fill NULLs
        nulls = Shop.objects.filter(public_id__isnull=True).count()
        if nulls:
            self.stdout.write(f"Found {nulls} shops with NULL public_id. Backfilling...")
            with transaction.atomic():
                for shop in Shop.objects.filter(public_id__isnull=True).iterator():
                    shop.public_id = uuid.uuid4()
                    shop.save(update_fields=["public_id"])
            self.stdout.write("NULLs backfilled.")
        else:
            self.stdout.write("No NULL public_id values found.")

        # Step 2: Check for duplicates
        dup_groups = (
            Shop.objects.values("public_id")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
        )

        total_dup_groups = dup_groups.count()
        if total_dup_groups:
            self.stdout.write(f"Found {total_dup_groups} duplicate UUID group(s). Fixing...")
            with transaction.atomic():
                for row in dup_groups:
                    # Keep the first shop, reassign others
                    dup_shops = list(
                        Shop.objects.filter(public_id=row["public_id"]).order_by("id")
                    )
                    for s in dup_shops[1:]:
                        s.public_id = uuid.uuid4()
                        s.save(update_fields=["public_id"])
            self.stdout.write("Duplicates fixed.")
        else:
            self.stdout.write("No duplicates found.")

        # Step 3: Final check
        nulls = Shop.objects.filter(public_id__isnull=True).count()
        dup_groups = (
            Shop.objects.values("public_id")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
        ).count()

        self.stdout.write(f"Final check -> NULLs: {nulls}, duplicate groups: {dup_groups}")
        self.stdout.write("Done.")
