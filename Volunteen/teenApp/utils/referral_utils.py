from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.utils.CampaignUtils import CampaignUtils
from teenApp.utils.NotificationManager import NotificationManager

FRIEND_REFERRAL_TASK_DATA = {
    "title": "חבר מביא חבר!",
    "description": (
        "תביא חבר שיצטרף לוולנטין ותקבל נקודות! כמה חברים תצליח לצרף השבוע?"
    ),
    "points": 5,
    "img": "defaults/friend_referral.png",
    "proof_required": True,
    "send_whatsapp_on_assign": True,
    "is_pinned": True,
    "valid_days": 7,
}

def _get_daily_referral_task(deadline, mentor):
    """
    Returns a shared active referral Task if one exists, or creates a new one.
    """
    today = timezone.localdate()
    existing = Task.objects.filter(
        title=FRIEND_REFERRAL_TASK_DATA["title"],
        deadline__gt=today
    ).order_by('-deadline').first()

    if existing:
        if mentor not in existing.assigned_mentors.all():
            existing.assigned_mentors.add(mentor)
        return existing

    # Create new task for today
    task = Task.objects.create(
        title=FRIEND_REFERRAL_TASK_DATA["title"],
        description=FRIEND_REFERRAL_TASK_DATA["description"],
        points=FRIEND_REFERRAL_TASK_DATA["points"],
        deadline=deadline,
        img=FRIEND_REFERRAL_TASK_DATA["img"],
        proof_required=FRIEND_REFERRAL_TASK_DATA["proof_required"],
        send_whatsapp_on_assign=FRIEND_REFERRAL_TASK_DATA["send_whatsapp_on_assign"],
        is_pinned=FRIEND_REFERRAL_TASK_DATA["is_pinned"],
    )
    task.assigned_mentors.add(mentor)
    return task

def child_needs_new_referral(child):
    """
    Checks if a child needs a new referral task (either never had one, or last one expired or completed).
    """
    today = timezone.now().date()
    assignments = TaskAssignment.objects.filter(
        child=child,
        task__title=FRIEND_REFERRAL_TASK_DATA["title"],
        refunded_at__isnull=True,
        task__deadline__gt=today,
    )

    completed_ids = TaskCompletion.objects.filter(
        child=child,
        task__in=assignments.values_list("task_id", flat=True),
    ).values_list("task_id", flat=True)

    return not assignments.exclude(task_id__in=completed_ids).exists()

@transaction.atomic
def recreate_referral_tasks_for_all():
    """
    Run daily at 10:00 AM. Creates ONE referral Task for today only if needed,
    and assigns it to children that have no active & uncompleted referral task.
    """
    mentor = CampaignUtils.get_campaign_mentor()
    today = timezone.now()
    deadline = today.date() + timezone.timedelta(days=FRIEND_REFERRAL_TASK_DATA["valid_days"])

    eligible_children = [
        c for c in mentor.children.exclude(id=237).select_related("user__personal_info")
        if hasattr(c, "subscription") and c.subscription.is_active()
    ]


    children_to_assign = [c for c in eligible_children if child_needs_new_referral(c)]

    if not children_to_assign:
        return "No referral task needed today – all children already have one"

    task = _get_daily_referral_task(deadline, mentor)

    TaskAssignment.objects.bulk_create([
        TaskAssignment(task=task, child=child, assigned_by=mentor.user)
        for child in children_to_assign
    ], ignore_conflicts=True)

    msg_template = (
            "🚀 אתגר חדש מחכה לך: חבר מביא חבר!\n"
            "תן לחברים שלך לגלות את Volunteen – וכשהם מתחילים להתנדב, אתה קוטף את הנקודות 🎯\n"
            "חבר = נקודות 💸  עוד חבר? עוד נקודות! פשוט, כיף, ומשתלם 😎\n"
            "אז שתף עכשיו והפוך למגייס האלוף של החודש 💪\n\n"
            "📲 כל הפרטים כאן: https://www.volunteen.site/child/home/\n"
            "👇 הולך להיות מעניין בוואטסאפ… באים? 😉\nhttp://bit.ly/3EXVxLL\n"
            "📸 עקבו אחרינו באינסטה:\nhttps://rb.gy/9i3yxf\n\n"
            "בהצלחה! – צוות Volunteen 🧡"
        )

    for child in children_to_assign:
        phone = getattr(child.user.personal_info, "phone_number", "")
        if phone:
            NotificationManager.sent_whatsapp(msg=msg_template, phone=phone)

    return f"Assigned {len(children_to_assign)} children to today's referral task"
