from django.utils import timezone
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.TaskCompletion import TaskCompletion
from childApp.utils.CampaignUtils import CampaignUtils
from teenApp.utils.NotificationManager import NotificationManager

FRIEND_REFERRAL_TASK_DATA = {
    "title": "חבר מביא חבר!",
    "description": (
        "כמה חברים תצליח לצרף החודש? כל חבר שמתחיל להתנדב שווה לך נקודות. הזמן עכשיו!"
    ),
    "points": 10,
    "img": "defaults/friend_referral.png",
    "proof_required": True,
    "send_whatsapp_on_assign": True,
    "is_pinned": True,
    # how many days the child gets to finish each copy
    "valid_days": 7,
}

def _clone_task_from_template(template_task, deadline):
    """
    Returns a NEW Task cloned from `template_task`, with a fresh deadline.
    """
    new_task = Task.objects.create(
        title=template_task.title,
        description=template_task.description,
        points=template_task.points,
        deadline=deadline,
        img=template_task.img,
        is_pinned=template_task.is_pinned,
        proof_required=template_task.proof_required,
        send_whatsapp_on_assign=template_task.send_whatsapp_on_assign,
    )
    new_task.assigned_mentors.set(template_task.assigned_mentors.all())
    return new_task

def recreate_referral_task_for_child(child):
    """
    If the child has no *active & uncompleted* friend-referral task,
    create a fresh copy and assign it. Returns True when a new task
    is generated, otherwise False.
    """
    now = timezone.now()
    MENTOR = CampaignUtils.get_campaign_mentor()
    deadline = now.date() + timezone.timedelta(days=FRIEND_REFERRAL_TASK_DATA["valid_days"])

    assignments = TaskAssignment.objects.filter(
        child=child,
        task__title=FRIEND_REFERRAL_TASK_DATA["title"],
        refunded_at__isnull=True,
        task__deadline__gt=now.date()
    )

    completed_task_ids = TaskCompletion.objects.filter(
        child=child,
        task__in=assignments.values_list("task_id", flat=True),
        status="approved"
    ).values_list("task_id", flat=True)

    active_uncompleted_exists = assignments.exclude(
        task_id__in=completed_task_ids
    ).exists()

    if active_uncompleted_exists:
        return False


    template_task = Task.objects.filter(
        title=FRIEND_REFERRAL_TASK_DATA["title"],
    ).first()

    if not template_task:
        template_task = Task.objects.create(
            title=FRIEND_REFERRAL_TASK_DATA["title"],
            description=FRIEND_REFERRAL_TASK_DATA["description"],
            points=FRIEND_REFERRAL_TASK_DATA["points"],
            deadline=deadline,
            img=FRIEND_REFERRAL_TASK_DATA["img"],
            is_template=False,
            is_pinned=FRIEND_REFERRAL_TASK_DATA["is_pinned"],
            proof_required=FRIEND_REFERRAL_TASK_DATA["proof_required"],
            send_whatsapp_on_assign=FRIEND_REFERRAL_TASK_DATA["send_whatsapp_on_assign"],
        )
        template_task.assigned_mentors.add(MENTOR)

    # Make a NEW copy for this cycle
    task_copy = _clone_task_from_template(template_task, deadline)

    # 4) Assign it to the child
    TaskAssignment.objects.create(
        task=task_copy,
        child=child,
        assigned_by=MENTOR.user,
    )

    # Notify the child
    

    if child.user.personal_info.phone_number:
        msg = (
            "🚀 אתגר חדש מחכה לך: חבר מביא חבר!\n"
            "תן לחברים שלך לגלות את Volunteen – וכשהם מתחילים להתנדב, אתה קוטף את הנקודות 🎯\n"
            "חבר = נקודות 💸  עוד חבר? עוד נקודות! פשוט, כיף, ומשתלם 😎\n"
            "אז שתף עכשיו והפוך למגייס האלוף של החודש 💪\n\n"
            "📲 כל הפרטים כאן: https://www.volunteen.site/child/home/\n"
            "👇 הולך להיות מעניין בוואטסאפ… באים? 😉\nhttp://bit.ly/3EXVxLL\n"
            "📸 עקבו אחרינו באינסטה:\nhttps://rb.gy/9i3yxf\n\n"
            "בהצלחה! – צוות Volunteen 🧡"
        )
        NotificationManager.sent_whatsapp(
            msg=msg,
            phone=child.user.personal_info.phone_number,
        )

    return True


#  Convenience wrapper: process ALL children (for Django-Q schedule)
def recreate_referral_tasks_for_all():
    mentor = CampaignUtils.get_campaign_mentor()
    children = mentor.children.exclude(id=237)

    created = 0
    for child in children:
        try:
            subscription = getattr(child, "subscription", None)
            if not subscription or not subscription.is_active():
                continue
            elif recreate_referral_task_for_child(child):
                created += 1
        except Exception as e:
            print(f"Failed to assign referral task to child {child.id}: {str(e)}")
            NotificationManager.sent_to_log_group_whatsapp(
                msg=f"Failed to assign referral task to child {child.id}: {str(e)}",
                phone=child.user.personal_info.phone_number,
            )

    return f"Friend-referral tasks created & notified: {created}"
