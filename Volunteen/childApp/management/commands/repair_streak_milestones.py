from django.core.management.base import BaseCommand
from django.utils import timezone
from childApp.models import Child,StreakMilestoneAchieved

children_streaks = [
    ("מחמד_פחר", 76),
    ("עבד_גפאלי", 44),
    ("איאד_חימל", 34),
    ("חסין_עיאש", 33),
    ("עבאס_אבן_חביש", 25),
    ("ריאן_גאלב", 19),
    ("יוסף_אחמד", 18),
    ("סעיד_גאלב", 17),
    ("ריאן_סלום", 16),
    ("אדם_כלבוני", 10),
    ("מוסטפא_אבן_שהאב", 9),
    ("אמיר_אבדאללה", 8),
    ("מחמד_אוסוף", 6),
    ("איוב_כלבוני", 6),
    ("מחמד_סוסה", 6),
    ("יוסף_ואקד", 5),
    ("חליל_גוטי", 5),
    ("איברהים_מנסור", 4),
    ("איברהים_זיבדה", 4),
    ("ג׳ינה_סעידי", 4),
    ("נור_גואאב", 4),
    ("יוסף_עבד_אלגאפר", 4),
    ("יוסף_זתוניה", 3),
    ("חאדר_זכה", 3),
]

class Command(BaseCommand):
    help = "Repair legacy streaks: update streak_count, last_streak_date, and create milestone records"

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        success, failed = 0, 0

        for full_name, raw_streak in children_streaks:
            try:
                child = Child.objects.get(user__username=full_name)
                new_streak = raw_streak + 1
                child.streak_count = new_streak
                child.last_streak_date = today
                child.save(update_fields=["streak_count", "last_streak_date"])

                # Create milestone records (every 10)
                for day in range(10, new_streak, 10):
                    StreakMilestoneAchieved.objects.get_or_create(
                        child=child,
                        streak_day=day
                    )

                success += 1
                self.stdout.write(self.style.SUCCESS(f"{full_name} ✅ updated to {new_streak}"))
            except Child.DoesNotExist:
                failed += 1
                self.stdout.write(self.style.ERROR(f"{full_name} ❌ not found"))

        self.stdout.write(self.style.SUCCESS(f"✅ Done: {success} updated"))
        if failed:
            self.stdout.write(self.style.WARNING(f"⚠️ {failed} children not found"))
