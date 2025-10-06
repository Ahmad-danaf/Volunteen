import time

from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

from childApp.models import Child
from managementApp.models import DonationSpending, SpendingAllocation
from teenApp.utils.NotificationManager import NotificationManager


def send_donation_thank_you_messages(child_ids, spending_id):
    """
    Async task triggered after a DonationSpending is created.

    - Fetches children involved in this spending.
    - Sends WhatsApp thank-you messages to each child and their parent.
    - Posts summary logs to WhatsApp group.
    """

    start_time = time.time()
    try:
        spending = DonationSpending.objects.select_related("shop", "category").get(id=spending_id)
        shop_name = spending.shop.name if spending.shop else "المجتمع"
        allocations = (
            SpendingAllocation.objects
            .filter(spending=spending, transaction__child_id__in=child_ids)
            .values("transaction__child_id")
            .annotate(total_used=Sum("amount_used"))
        )
        amount_map = {a["transaction__child_id"]: a["total_used"] for a in allocations}
        children = (
            Child.objects.filter(id__in=child_ids)
            .select_related("user", "parent__user")
            .prefetch_related("user__personal_info")
        )
        total_children = len(child_ids)
        total_parents = 0
        success_count_children = 0
        success_count_parents = 0

        for child in children:
            child_phone = child.phone_number
            child_name = child.user.username.split("_")[0]
            amount_used = str(amount_map.get(child.id, 0)) + " Teencoins"
            msg_child = (
                f"جزاك الله خيرًا {child_name}!\n"
                f"تم صرف {amount_used} في {shop_name}، عمل رائع منك! 🌟\n"
                f"قال رسول الله ﷺ: \"أحب الناس إلى الله أنفعهم للناس\" (رواه الطبراني)"
            )
            sent_child = False
            if child_phone:
                sent_child = NotificationManager.sent_whatsapp(msg_child, child_phone)
                time.sleep(0.15) 

            parent = getattr(child, "parent", None)
            sent_parent = False
            if parent and hasattr(parent, "user") and hasattr(parent.user, "personal_info"):
                parent_phone = parent.user.personal_info.phone_number
                if parent_phone:
                    total_parents += 1
                    msg_parent = (
                        f"جزاك الله خيرًا على دعمك لِـ {child_name} وتشجيعه على أعمال الخير!\n"
                        f"تبرعه بـ{amount_used} في {shop_name} له أثر كبير. 🙏\n"
                        f"قال رسول الله ﷺ: \"أحب الناس إلى الله أنفعهم للناس\" (رواه الطبراني)"
                    )
                    sent_parent = NotificationManager.sent_whatsapp(msg_parent, parent_phone)

            if sent_child:
                success_count_children += 1
            if sent_parent:
                success_count_parents += 1

        duration = round(time.time() - start_time, 2)
        summary = (
            f"✅ Donation Thank-You Task Completed\n"
            f"Spending ID: {spending_id}\n"
            f"Category: {spending.category.name}\n"
            f"Shop: {shop_name}\n"
            f"Children: {total_children}\n"
            f"Success: {success_count_children}/{total_children}\n"
            f"Parents Success: {success_count_parents}/{total_parents}\n"
            f"Duration: {duration}s\n\n"
        )
        NotificationManager.sent_to_log_group_whatsapp(summary)

    except Exception as e:
        err_msg = f"[ERROR] Donation Thank-You Task Failed\nSpending ID: {spending_id}\nError: {str(e)}"
        print(err_msg)
        NotificationManager.sent_to_log_group_whatsapp(err_msg)
