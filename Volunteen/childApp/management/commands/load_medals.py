import os
import json
from django.core.management.base import BaseCommand
from childApp.models import Medal

class Command(BaseCommand):
    help = "Load medals from a JSON file into the database."

    def handle(self, *args, **options):
        # קובץ JSON של המדליות
        file_path = os.path.join(os.path.dirname(__file__), '../../utilities/data/medals.json')

        try:
            # פתיחת הקובץ וטעינת הנתונים
            with open(file_path, 'r', encoding='utf-8') as f:
                medals_data = json.load(f)

            # לולאה על כל המדליות בקובץ וטעינה לדאטהבייס
            for medal_data in medals_data:
                medal, created = Medal.objects.update_or_create(
                    name=medal_data['name'],
                    defaults={
                        'description': medal_data['description'],
                        'points_reward': medal_data['points_reward'],
                        'criterion': medal_data['criterion']
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"מדליה חדשה נוספה: {medal.name}"))
                else:
                    self.stdout.write(self.style.WARNING(f"מדליה עודכנה: {medal.name}"))
            
            self.stdout.write(self.style.SUCCESS("כל המדליות נטענו בהצלחה!"))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"קובץ JSON לא נמצא: {file_path}"))
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR("שגיאה בפענוח קובץ ה-JSON"))
