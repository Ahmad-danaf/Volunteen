from django.contrib import messages
from django.shortcuts import render, redirect
from managementApp.decorators import superadmin_required
from django.views import View
from typing import List
from django.utils.decorators import method_decorator
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from managementApp.forms.superAdmin import ProofBulkForm
from institutionApp.models import Institution
from mentorApp.models import Mentor
from childApp.models import Child, ChildBan,BanScope,DEFAULT_BAN_NOTES
from teenApp.entities import TaskProofRequirement
from managementApp.utils.superadmin import *
from managementApp.decorators import superadmin_required

@superadmin_required
def upload_menu_view(request):
    """
    SuperAdmin upload menu that lets them choose between
    uploading children, mentors, shops, or institutions via CSV.
    """
    upload_options = [
        {
            "title": "העלאת ילדים מקובץ CSV",
            "icon_color": "indigo-400",
            "url_name": "managementApp:upload_children_csv",
            "svg_path": "M12 4v16m8-8H4"
        },
        {
            "title": "העלאת מנטורים",
            "icon_color": "blue-400",
            "url_name": "managementApp:coming_soon",
            "svg_path": "M5.121 17.804A7.963 7.963 0 0112 16c1.657 0 3.182.506 4.379 1.362"
        },
        {
            "title": "העלאת מוסדות",
            "icon_color": "green-400",
            "url_name": "managementApp:coming_soon",  
            "svg_path": "M3 10h18M5 6h14M7 14h10"
        },
        {
            "title": "העלאת חנויות",
            "icon_color": "pink-400",
            "url_name": "managementApp:coming_soon",
            "svg_path": "M3 3h18v6H3z M5 9v12h14V9"
        }
    ]
    
    return render(request, "superadmin/upload_menu.html", {"upload_options": upload_options})



@superadmin_required
def upload_children_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file or not csv_file.name.endswith(".csv"):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect("managementApp:upload_children_csv")

        rows = UserCreationUtility.parse_csv(csv_file)
        logs = []
        total_rows = 0
        total_created_children = 0
        total_skipped_children = 0
        total_created_subscriptions = 0
        total_updated_subscriptions = 0
        total_non_provided_subscriptions = 0
        for i, row in enumerate(rows, start=2):
            total_rows += 1
            success, log = UserCreationUtility.create_child_from_row(row)
            log["row"] = i-1
            logs.append(log)
            
            if log.get("created_user", False):                     
                total_created_children += 1
            else:
                total_skipped_children += 1
            if log.get("subscription_action") == "Created":
                total_created_subscriptions += 1
            elif log.get("subscription_action") == "Updated":
                total_updated_subscriptions += 1
            elif log.get("subscription_action") == "Not provided":
                total_non_provided_subscriptions += 1
                
        context = {
            "logs": logs,
            "summary": {
                "total_rows": total_rows,
                "total_created_children": total_created_children,
                "total_skipped_children": total_skipped_children,
                "total_created_subscriptions": total_created_subscriptions,
                "total_updated_subscriptions": total_updated_subscriptions,
                "total_non_provided_subscriptions": total_non_provided_subscriptions,
            }
        }
        return render(request, "superadmin/upload_child_users.html", context)

    return render(request, "superadmin/upload_child_users.html")


@superadmin_required
def superadmin_dashboard(request):
    """
    Render the Super Admin dashboard.
    """
    return render(request, "superadmin/superadmin_dashboard.html")


@superadmin_required
def coming_soon(request):
    """
    Render a 'Coming Soon' page for the Super Admin.
    """
    return render(request, "feature_not_completed.html")

@superadmin_required
def permission_settings(request):
    """
    Render the permission settings page for the Super Admin.
    """
    return render(request, "superadmin/permission/permission_settings.html")


@method_decorator(superadmin_required, name="dispatch")
class SuperadminProofOptionsView(View):
    template_name = "superadmin/proof_options.html"

    def get(self, request):
        form = ProofBulkForm()
        institutions = Institution.objects.order_by("name").values("id", "name")
        mentors = (
            Mentor.objects.select_related("user")
            .prefetch_related("institutions")
            .order_by("user__username")
        )

        mentor_rows = []
        for m in mentors:
            mentor_rows.append({
                "id": m.id,
                "username": m.user.username,
                "first_name": m.user.first_name or "",
                "last_name": m.user.last_name or "",
                "institutions": [i.id for i in m.institutions.all()],
                "institutions_names": [i.name for i in m.institutions.all()],
                "allowed": list(m.allowed_proof_options or []),
            })

        context = {
            "form": form,
            "institutions": list(institutions),
            "mentors_data": mentor_rows,
            "proof_choices": list(TaskProofRequirement.choices),
            "hot_presets": [
                (TaskProofRequirement.AUTO_ACCEPT_CHECKIN, "אישור אוטומטי אחרי Check-in"),
                (TaskProofRequirement.AUTO_ACCEPT_CHECKOUT, "אישור אוטומטי אחרי Check-out"),
                (TaskProofRequirement.NO_PROOF_REQUIRED, "ללא צורך בתמונה"),
            ],
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ProofBulkForm(request.POST)
        if not form.is_valid():
            messages.error(request, "בדיקת טופס נכשלה. ודא שבחרת פעולה ואפשרויות הוכחה.")
            return redirect("managementApp:superadmin_proof_options")

        mentors: List[Mentor] = list(form.cleaned_data["mentors"])
        action = form.cleaned_data["action"]
        proof_options = form.cleaned_data["proof_options"] 

        if not mentors:
            messages.warning(request, "לא נבחרו מנטורים.")
            return redirect("managementApp:superadmin_proof_options")
        if not proof_options:
            messages.warning(request, "לא נבחרו אפשרויות הוכחה.")
            return redirect("managementApp:superadmin_proof_options")

        updated = 0
        with transaction.atomic():
            for m in mentors:
                current = set(m.allowed_proof_options or [])
                before = current.copy()
                if action == "add":
                    current.update(proof_options)
                else:  
                    current.difference_update(proof_options)
                if current != before:
                    m.allowed_proof_options = sorted(list(current))
                    m.save(update_fields=["allowed_proof_options"])
                    updated += 1

        messages.success(request, f"בוצע בהצלחה: עודכנו {updated} מנטורים.")
        return redirect("managementApp:superadmin_proof_options")
    
    
@method_decorator(superadmin_required, name="dispatch")
class SuperadminBansDashboardView(View):
    template_name = "superadmin/ban/bans_dashboard.html"

    def get(self, request):
        now = timezone.now()

        active_bans = BanQueryUtils.list_active_bans(at=now)
        active_children_rows = BanQueryUtils.children_with_active_bans(at=now)

        kpis = {
            "total_active_bans": len(active_bans),
            "total_active_children": len(active_children_rows),
            "total_bans_all_time": BanQueryUtils.all_bans_qs().count(),
            "unique_children_all_time": BanQueryUtils.all_bans_qs().values("child_id").distinct().count(),
        }

        paginator = Paginator(active_children_rows, 15)
        page_obj = paginator.get_page(request.GET.get("page") or 1)

        context = {
            "now": now,
            "kpis": kpis,
            "page_obj": page_obj,               
            "top_days": BanAnalytics.top_by_total_days(limit=10, at=now),
            "top_bans": BanAnalytics.top_by_bans_count(limit=10, at=now),
        }
        return render(request, self.template_name, context)
    
    
@method_decorator(superadmin_required, name="dispatch")
class SuperadminBanCreateView(View):
    template_name = "superadmin/ban/bans_create.html"

    def get(self, request):
        children_qs = (
            Child.objects.select_related("user")
            .order_by("user__username")
        )
        context = {
            "now": timezone.localtime(),
            "children":  prepare_child_data(children_qs),
            "scope_choices": [
                (BanScope.PURCHASE, "רכישות"),
                (BanScope.CAMPAIGN, "קמפיינים"),
                (BanScope.ALL, "הכול"),
            ],
            "severity_choices": [("soft", "רך"), ("hard", "חמור")],
            "preset_choices": [
                ("1", "1 יום"),
                ("3", "3 ימים"),
                ("7", "7 ימים"),
                ("14", "14 ימים"),
                ("30", "30 ימים"),
                ("eod_il", "עד סוף היום"),
                ("indefinite", "ללא הגבלת זמן"),
            ],
            "default_notes": {
                str(BanScope.PURCHASE): DEFAULT_BAN_NOTES[BanScope.PURCHASE],
                str(BanScope.CAMPAIGN): DEFAULT_BAN_NOTES[BanScope.CAMPAIGN],
                str(BanScope.ALL): DEFAULT_BAN_NOTES[BanScope.ALL],
            },
        }
        return render(request, self.template_name, context)

    @transaction.atomic
    def post(self, request):
        child_ids = (request.POST.get("child_ids") or "").strip()
        scope     = request.POST.get("scope")
        severity  = (request.POST.get("severity") or "hard").strip() or "hard"
        starts_raw= (request.POST.get("starts_at") or "").strip()
        ends_raw  = (request.POST.get("ends_at") or "").strip()
        note_child= (request.POST.get("note_child") or "").strip()
        note_staff= (request.POST.get("note_staff") or "").strip()
        
        try:
            child_ids_list = [int(x) for x in child_ids.split(",") if x]
        except Exception:
            child_ids_list = []

        if not child_ids_list:
            messages.error(request, "יש לבחור לפחות ילד אחד.")
            return redirect(reverse("managementApp:superadmin_bans_create"))

        valid_scopes = {choice[0] for choice in BanScope.choices}
        if scope not in valid_scopes:
            scope = BanScope.PURCHASE

        if severity not in {"hard", "soft"}:
            severity = "hard"

        def _parse_any(dt_str: str):
            dt = None
            try:
                dt = timezone.datetime.fromisoformat(dt_str)
            except Exception:
                dt = parse_datetime(dt_str)
            if dt is None:
                return None
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        starts_at = _parse_any(starts_raw)
        if not starts_at:
            messages.error(request, "תאריך התחלה לא תקין.")
            return redirect(reverse("managementApp:superadmin_bans_create"))

        ends_at = None
        if ends_raw:
            ends_at = _parse_any(ends_raw)
            if not ends_at:
                messages.error(request, "תאריך סיום לא תקין.")
                return redirect(reverse("managementApp:superadmin_bans_create"))

        if ends_at and ends_at <= starts_at:
            messages.error(request, "תאריך הסיום חייב להיות אחרי תאריך ההתחלה.")
            return redirect(reverse("managementApp:superadmin_bans_create"))

        child_ids_set = set(child_ids_list)
        child_usernames = {
            c.id: c.user.username
            for c in Child.objects.filter(id__in=child_ids_set).select_related("user").only("id", "user__username")
        }
        active_same_scope_ids = UserCreationUtility.ids_with_active_ban_in_scope(child_ids_set, scope)
        created = 0
        skipped = []

        for cid in child_ids_set:
            if cid in active_same_scope_ids:
                skipped.append(child_usernames.get(cid, str(cid)))
                continue

            create_kwargs = dict(
                child_id=cid,
                scope=scope,
                starts_at=starts_at,
                ends_at=ends_at,          
                note_staff=note_staff,
                severity=severity,
                created_by=request.user,
            )
            if note_child: 
                create_kwargs["note_child"] = note_child

            ChildBan.objects.create(**create_kwargs)
            created += 1

        if created:
            messages.success(request, f"חסימות נוצרו בהצלחה: {created}")
        if skipped:
            sample = "، ".join(skipped[:5])
            more = len(skipped) - 5
            suffix = f" ועוד {more}…" if more > 0 else ""
            messages.warning(request, f"דלגנו על חסימות עבור: {sample}{suffix} — קיימת כבר חסימה פעילה לאותו תחום.")

        return redirect(reverse("managementApp:superadmin_bans_dashboard"))