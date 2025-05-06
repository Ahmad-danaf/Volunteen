from django.core.management.base import BaseCommand
from shopApp.models import Redemption
from django.utils import timezone
from datetime import timedelta
from teenApp.utils.NotificationManager import NotificationManager
from django.utils.timezone import make_aware
from datetime import datetime

class Command(BaseCommand):
    help = 'Log suspicious events (e.g., clustered redemptions) to WhatsApp group'

    def handle(self, *args, **kwargs):
        self.stdout.write("###############START OF CHECKING###############")
        self.stdout.write("Checking for suspicious activity...")
        
        self.check_redeem_clusters()
        self.scan_suspicious_tasks()
        
        self.stdout.write("###############END OF CHECKING###############")

        # Future: self.check_task_thresholds() or others...

    def check_redeem_clusters(self):
        """Find clusters of redemptions that happened within 20-minute windows."""
        time_threshold = timedelta(minutes=20)
        min_cluster_size = 3
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        start = make_aware(datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0))
        end = make_aware(datetime(now.year, now.month, now.day, 0, 0, 0))

        recent_redemptions = Redemption.objects.filter(
            date_redeemed__gte=start,
            date_redeemed__lt=end
        ).order_by('date_redeemed')


        clusters = []
        current_cluster = []

        for redemption in recent_redemptions:
            if not current_cluster:
                current_cluster.append(redemption)
            else:
                last_time = current_cluster[-1].date_redeemed
                if redemption.date_redeemed - last_time <= time_threshold:
                    current_cluster.append(redemption)
                else:
                    if len(current_cluster) >= min_cluster_size:
                        clusters.append(current_cluster)
                    current_cluster = [redemption]

        # Check last group
        if len(current_cluster) >= min_cluster_size:
            clusters.append(current_cluster)

        for cluster in clusters:
            self.send_cluster_log(cluster)

    def send_cluster_log(self, cluster):
        """Format and send redemption cluster log to WhatsApp group."""
        if not cluster:
            return
        timespan_start = cluster[0].date_redeemed.strftime('%Y-%m-%d %H:%M')
        timespan_end = cluster[-1].date_redeemed.strftime('%H:%M')
        msg_lines = [
            f"🚨 *Suspicious Redemption Cluster* 🚨",
            f"🕒 Time: {timespan_start} - {timespan_end}",
            f"📦 Count: {len(cluster)} redemptions",
            "",
        ]
        for redemption in cluster:
            msg_lines.append(
                f"- {redemption.child.user.username} redeemed {redemption.quantity}x {redemption.reward.title} "
                f"({redemption.points_used} pts) at {redemption.shop.name}"
            )

        message = "\n".join(msg_lines)
        NotificationManager.sent_to_log_group_whatsapp(message)
        self.stdout.write("Logged suspicious redemption cluster to WhatsApp.")
        
        
    def scan_suspicious_tasks(self):
        """Scan for suspicious task activity and log to WhatsApp."""
        from teenApp.entities.task import Task
        from teenApp.entities.TaskAssignment import TaskAssignment
        from teenApp.entities.TaskCompletion import TaskCompletion
        from django.utils import timezone
        from django.db.models import Count, Q
        from django.db.models.functions import Length
        

        self.stdout.write(" Scanning for suspicious tasks...")
        # Configurable thresholds
        DAYS_BACK = 7
        MIN_TITLE_LENGTH = 3
        HIGH_POINTS_THRESHOLD = 50
        RAPID_COMPLETION_THRESHOLD = timedelta(minutes=5)

        # Time range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=DAYS_BACK)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nScanning for suspicious tasks (last {DAYS_BACK} days) "
            f"[{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}]\n"
        ))

        # 1. Short title tasks
        self.stdout.write(self.style.HTTP_INFO("\n=== Checking for short task titles ==="))
        short_title_tasks = Task.objects.annotate(
            title_len=Length('title')
        ).filter(
            Q(assignments__assigned_at__gte=start_date) &
            Q(title_len__lt=MIN_TITLE_LENGTH)
        ).distinct()

        if short_title_tasks.exists():
            self.stdout.write(self.style.WARNING(f"Found {short_title_tasks.count()} tasks with short titles:"))
            for task in short_title_tasks:
                self.stdout.write(
                    f"ID: {task.id} | Title: '{task.title}' ({len(task.title)} chars) "
                    f"| Points: {task.points} | Creator: {self.get_creator_info(task)}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("No tasks with suspiciously short titles found"))

        # 2. High-point tasks
        self.stdout.write(self.style.HTTP_INFO("\n=== Checking for high-point tasks ==="))
        high_point_tasks = Task.objects.filter(
            Q(points__gte=HIGH_POINTS_THRESHOLD) &
            Q(assignments__assigned_at__gte=start_date)
        ).distinct()

        if high_point_tasks.exists():
            self.stdout.write(self.style.WARNING(f"Found {high_point_tasks.count()} high-point tasks:"))
            for task in high_point_tasks:
                recent_assignments = task.assignments.filter(assigned_at__gte=start_date).count()
                self.stdout.write(
                    f"ID: {task.id} | Title: '{task.title}' | "
                    f"Points: {task.points} | Recent assignments: {recent_assignments}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("No high-point tasks detected"))

        # 3. Rapid completions
        self.stdout.write(self.style.HTTP_INFO("\n=== Checking for rapid completions ==="))
        rapid_completions = []
        recent_completions = TaskCompletion.objects.filter(
            completion_date__gte=start_date,
            status='approved'
        ).select_related('task', 'child')

        for completion in recent_completions:
            assignment = TaskAssignment.objects.filter(
                task=completion.task,
                child=completion.child
            ).order_by('assigned_at').first()

            if assignment and completion.completion_date:
                time_to_complete = completion.completion_date - assignment.assigned_at
                if time_to_complete < RAPID_COMPLETION_THRESHOLD:
                    rapid_completions.append({
                        'task': completion.task,
                        'child': completion.child,
                        'time_to_complete': time_to_complete,
                        'points': completion.task.points
                    })

        if rapid_completions:
            self.stdout.write(self.style.WARNING(f"Found {len(rapid_completions)} rapid completions:"))
            for rc in rapid_completions:
                self.stdout.write(
                    f" Task: '{rc['task'].title}' | Child: {rc['child'].user.username} | "
                    f"Completed in: {rc['time_to_complete']} | Points: {rc['points']}"
                )
        else:
            self.stdout.write(self.style.SUCCESS("No suspiciously rapid completions found"))

        # Summary + WhatsApp report
        self.stdout.write(self.style.MIGRATE_HEADING("\nScan Summary:"))
        self.stdout.write(
            f"• Short title tasks: {short_title_tasks.count()}\n"
            f"• High-point tasks: {high_point_tasks.count()}\n"
            f"• Rapid completions: {len(rapid_completions)}\n"
        )
        self.stdout.write(self.style.SUCCESS("Suspicious task scan completed!"))

        self.send_whatsapp_log(short_title_tasks, high_point_tasks, rapid_completions, start_date, end_date)

    def get_creator_info(self, task):
        """Get information about task creator with fallback to assigned mentors"""
        first_assignment = task.assignments.order_by('assigned_at').first()
        if first_assignment and first_assignment.assigned_by:
            return f"{first_assignment.assigned_by.username} (ID: {first_assignment.assigned_by.id})"
        mentor = task.assigned_mentors.first()
        if mentor:
            return f"Mentor: {mentor.user.username} (ID: {mentor.user.id})"
        return "Unknown creator"

    def send_whatsapp_log(self, short_title_tasks, high_point_tasks, rapid_completions, start_date, end_date):
        """Format and send suspicious activity summary to WhatsApp log group."""
        msg = [
            f"🚨 *Suspicious Task Activity Detected*",
            f"🗓️ *Period:* {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "",
            f"📝 *Short Titles:* {short_title_tasks.count()}",
            f"💰 *High-Point Tasks:* {high_point_tasks.count()}",
            f"⏱️ *Rapid Completions:* {len(rapid_completions)}",
            ""
        ]

        if short_title_tasks.exists():
            msg.append("🔹 *Short Title Examples:*")
            for task in short_title_tasks[:3]:
                msg.append(f"- '{task.title}' ({len(task.title)} chars), {task.points} pts")

        if high_point_tasks.exists():
            msg.append("\n🔹 *High-Point Task Examples:*")
            for task in high_point_tasks[:3]:
                msg.append(f"- '{task.title}', {task.points} pts")

        if rapid_completions:
            msg.append("\n🔹 *Rapid Completions:*")
            for rc in rapid_completions[:3]:
                msg.append(
                    f"- '{rc['task'].title}' by {rc['child'].user.username} in {rc['time_to_complete']}"
                )

        msg.append("\n📍 _System auto-scan at 2:00 AM_")
        NotificationManager.sent_to_log_group_whatsapp("\n".join(msg))
