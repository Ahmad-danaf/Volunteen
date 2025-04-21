import csv
from django.core.management.base import BaseCommand
from childApp.models import Child
from institutionApp.models import Institution
from django.db import transaction

class Command(BaseCommand):
    help = "Update institutions for existing children (CSV columns: identifier, institution)"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        self.stdout.write("############# Starting institution update ##############")
        
        updated = 0
        skipped = 0
        errors = 0
        
        try:
            with open(csv_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row_num, row in enumerate(reader, start=2):  # Row numbering starts at 2 (header = 1)
                    try:
                        identifier = row['identifier'].strip().zfill(5)  # Ensure 5-digit format
                        institution_name = row['institution'].strip()
                        username = row['username'].strip()
                        self.stdout.write(f"\nProcessing row {row_num}: {identifier}")
                        
                        # Find the child (skip if not found)
                        child = Child.objects.filter(identifier=identifier, user__username=username).first()
                        if not child:
                            skipped += 1
                            self.stdout.write(f"  - Child not found: {identifier}")
                            continue
                        
                        # Find the institution (skip if not found)
                        institution = Institution.objects.filter(name=institution_name).first()
                        if not institution:
                            skipped += 1
                            self.stdout.write(f"  - Institution not found: {institution_name}")
                            continue
                        
                        # Update the child's institution
                        child.institution = institution
                        child.save()
                        updated += 1
                        self.stdout.write(f"  - Updated institution: {institution_name}")
                    
                    except Exception as e:
                        errors += 1
                        self.stdout.write(f"[Row {row_num}] Error: {e}")
        
        except FileNotFoundError:
            self.stdout.write(f"File not found: {csv_file}")
            return
        
        # Print summary
        self.stdout.write("\n=== Update Summary ===")
        self.stdout.write(f"Children updated: {updated}")
        self.stdout.write(f"Rows skipped (child/institution not found): {skipped}")
        self.stdout.write(f"Errors encountered: {errors}")
        self.stdout.write("############# Institution update completed ##############")