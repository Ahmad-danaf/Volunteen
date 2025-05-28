import csv
import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from teenApp.entities.task import Task
from mentorApp.models import Mentor
from childApp.models import Child
from mentorApp.utils.MentorTaskUtils import MentorTaskUtils
import datetime

class Command(BaseCommand):
    help = 'Import tasks from tasks_for_volunteen.csv and assign them to predefined users'

    def handle(self, *args, **options):
        path = os.path.join('tasks_for_volunteen.csv')  # Adjust path if needed
        today = datetime.datetime.today()

        try:
            with open(path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                # Fetch mentor and children once
                mentor = Mentor.objects.filter(user__username="Volunteen_mentor").first()
                child1 = Child.objects.filter(user__username="آدم_تكروري").first()
                child2 = Child.objects.filter(user__username="أحمد_دنف").first()

                if not all([mentor, child1, child2]):
                    if not mentor:
                        print("❌ Mentor not found.")
                    if not child1:
                        print("❌ Child 1 (آدم_تكروري) not found.")
                    if not child2:
                        print("❌ Child 2 (أحمد_دنف) not found.")
                    return

                for idx, row in enumerate(reader):
                    title = row.get("title", "").strip()
                    deadline_str = row.get("deadline", "").strip()
                    period = int(row.get("period", 1))
                    description = row.get("description", "").strip()
                    points = int(row.get("points (3)", 1))
                    repetitions = int(row.get("repetitions", 1))

                    deadline = today
                    if deadline < datetime.datetime.now().date():
                        self.stdout.write(f"⏭ Skipping past deadline for task: {title} {deadline}")
                        continue


                    # Determine assigned children
                    assigned_to_raw = row.get("assigned_to", "").strip()
                    if assigned_to_raw == "לשנינו":
                        assigned_children = [child1, child2]
                    elif assigned_to_raw == "אחמד":
                        assigned_children = [child2]
                    elif assigned_to_raw == "אדם":
                        assigned_children = [child1]
                    else:
                        self.stdout.write(f"⏭ Skipping unknown assigned_to '{assigned_to_raw}' for task: {title}")
                        continue



                    if period > 0:
                        if today.weekday() == 6 or period==1:
                            task_data = {
                                "title": title,
                                "deadline": deadline + timedelta(days=1 * period),
                                "description": description,
                                "points": points,
                                "send_whatsapp_on_assign": False,
                            }

                            MentorTaskUtils.create_task_with_assignments(
                                mentor=mentor,
                                children_ids=[child.id for child in assigned_children],
                                task_data=task_data,
                                timewindow_data=[],
                            )

                            self.stdout.write(f"✅ Created task '{title}' for {assigned_to_raw} on {task_data['deadline']:%d/%m/%Y}")

        except FileNotFoundError:
            self.stderr.write("❌ File not found: tasks_for_volunteen.csv")
