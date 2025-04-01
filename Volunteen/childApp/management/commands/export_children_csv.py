import csv
from django.core.management.base import BaseCommand
from childApp.models import Child  

class Command(BaseCommand):
    help = "Export child data (identifier and username) to a CSV file."

    def handle(self, *args, **options):
        output_file = "child_data_export.csv"
        
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                # Write header row
                writer.writerow(["Child Identifier", "Child Username"])
                
                # Write each child's data
                for child in Child.objects.all():
                    writer.writerow([child.identifier, child.user.username])
            
            self.stdout.write(self.style.SUCCESS(f"Exported child data to {output_file}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error exporting child data: {e}"))
