from datetime import datetime, time
import json

from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404,render
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction

from teenApp.entities import Task, TaskRecurrence, Frequency, RecurringRun
from mentorApp.utils.MentorTaskRecurrenceUtils import MentorTaskRecurrenceUtils

@login_required
@require_POST
def create_recurrence(request, task_id):
    mentor = request.user.mentor
    task = get_object_or_404(Task, id=task_id, assigned_mentors=mentor, is_template=True)
    if hasattr(task, "recurrence"):
        return JsonResponse({"success": False, "message": "כבר קיימת משימה חוזרת לתבנית זו."}, status=400)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"success": False, "message": f"שגיאת JSON ({e})"}, status=400)

    frequency = data.get("frequency", Frequency.DAILY)
    run_time_str = data.get("run_time_local", "10:00")
    interval_days = data.get("interval_days")
    by_weekday = data.get("by_weekday", [])
    day_of_month = data.get("day_of_month")
    end_date_str = data.get("end_date")
    deadline_offset_days = data.get("deadline_offset_days")
    
    try:
        hours, minutes = map(int, str(run_time_str).split(":"))
        run_time = time(hours, minutes)
    except Exception:
        run_time = time(10, 0)

    try:
        interval_days = int(interval_days) if interval_days else None
    except Exception:
        interval_days = None

    try:
        day_of_month = int(day_of_month) if day_of_month else None
    except Exception:
        day_of_month = None

    if isinstance(by_weekday, int):
        by_weekday = [by_weekday]
    elif isinstance(by_weekday, list):
        by_weekday = sorted(set(int(x) for x in by_weekday if str(x).isdigit() and 0 <= int(x) <= 6))
    else:
        by_weekday = []
        
    try:
        deadline_offset_days = int(deadline_offset_days) if deadline_offset_days else None
    except Exception:
        deadline_offset_days = None

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.strptime(str(end_date_str), "%Y-%m-%d").date()
        except Exception:
            return JsonResponse({"success": False, "message": "תאריך סיום לא תקין."}, status=400)

    rec = TaskRecurrence.objects.create(
        task=task,
        frequency=frequency,
        interval_days=interval_days if frequency == Frequency.EVERY_X_DAYS else None,
        by_weekday=by_weekday if frequency == Frequency.WEEKLY else [],
        day_of_month=day_of_month if frequency == Frequency.MONTHLY else None,
        run_time_local=run_time,
        start_date=timezone.localdate(),
        end_date=end_date,
        is_active=True,
        deadline_offset_days=deadline_offset_days,
    )

    return JsonResponse({
        "success": True,
        "message": f"המשימה נוספה כחוזרת ({rec.get_frequency_display()})",
        "recurrence_id": rec.id,
    })
    


@login_required
@require_GET
def recurrence_list(request):
    """
    GET /mentor/recurrences/?q=&status=(active|inactive|all)&freq=&page=&page_size=
    Returns mentor-scoped recurrence cards.
    """
    mentor = request.user.mentor
    qs = MentorTaskRecurrenceUtils._mentor_guard_qs(mentor).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(task__title__icontains=q)

    status = (request.GET.get("status") or "all").lower()
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    freq = request.GET.get("freq")
    if freq in dict(Frequency.choices):
        qs = qs.filter(frequency=freq)

    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 12))
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    data = [MentorTaskRecurrenceUtils._serialize_recurrence(rec) for rec in page_obj.object_list]
    return JsonResponse({
        "success": True,
        "data": data,
        "pagination": {
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "total": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    })


@login_required
def recurrence_dashboard_page(request):
    mentor = getattr(request.user, "mentor", None)
    if not mentor:
        return JsonResponse({"success": False, "message": "משתמש לא מורשה."}, status=403)

    return render(request, "mentorApp/recurrence/recurrence_dashboard.html", {"mentor": mentor})

@login_required
@require_GET
def recurrence_detail(request, rec_id: int):
    """
    GET /mentor/recurrences/<rec_id>/
    Detail for editing modal
    """
    mentor = request.user.mentor
    rec = MentorTaskRecurrenceUtils._mentor_get_recurrence_or_404(mentor, rec_id)
    return JsonResponse({"success": True, "data": MentorTaskRecurrenceUtils._serialize_recurrence(rec)})


@login_required
@require_http_methods(["PATCH", "POST"])
def recurrence_toggle_active(request, rec_id: int):
    """
    PATCH /mentor/recurrences/<rec_id>/toggle/
    Body: {"is_active": true/false}
    """
    mentor = request.user.mentor
    rec = MentorTaskRecurrenceUtils._mentor_get_recurrence_or_404(mentor, rec_id)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    is_active = payload.get("is_active")
    if isinstance(is_active, str):
        is_active = is_active.lower() in ("true", "1", "yes", "on")

    if is_active is None:
        return JsonResponse({"success": False, "message": "Missing 'is_active'."}, status=400)

    rec.is_active = bool(is_active)
    rec.save(update_fields=["is_active", "updated_at"])
    return JsonResponse({"success": True, "message": "עודכן סטטוס המשימה החוזרת.", "data": MentorTaskRecurrenceUtils._serialize_recurrence(rec)})


@login_required
@require_http_methods(["PATCH", "POST"])
@transaction.atomic
def recurrence_update(request, rec_id: int):
    """
    PATCH /mentor/recurrences/<rec_id>/update/
    Body: any of frequency, interval_days, by_weekday, day_of_month, run_time_local, end_date, start_date(optional)
    Notes:
    - Clears irrelevant fields based on frequency
    - Validates end_date >= start_date when both provided
    """
    mentor = request.user.mentor
    rec = MentorTaskRecurrenceUtils._mentor_get_recurrence_or_404(mentor, rec_id)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"success": False, "message": f"שגיאת JSON ({e})"}, status=400)

    frequency = data.get("frequency", rec.frequency)
    if frequency not in dict(Frequency.choices):
        return JsonResponse({"success": False, "message": "תדירות לא חוקית."}, status=400)

    interval_days = MentorTaskRecurrenceUtils._int_or_none(data.get("interval_days") if frequency == Frequency.EVERY_X_DAYS else None)
    by_weekday = MentorTaskRecurrenceUtils._int_list(data.get("by_weekday") if frequency == Frequency.WEEKLY else [])
    day_of_month = MentorTaskRecurrenceUtils._int_or_none(data.get("day_of_month") if frequency == Frequency.MONTHLY else None)
    run_time_local = MentorTaskRecurrenceUtils._parse_time_hhmm(data.get("run_time_local", rec.run_time_local.strftime("%H:%M")))
    start_date = MentorTaskRecurrenceUtils._parse_date_yyyy_mm_dd(data.get("start_date")) or rec.start_date
    end_date = MentorTaskRecurrenceUtils._parse_date_yyyy_mm_dd(data.get("end_date"))

    if end_date and end_date < start_date:
        return JsonResponse({"success": False, "message": "תאריך הסיום חייב להיות אחרי תאריך ההתחלה."}, status=400)

    rec.frequency = frequency
    rec.interval_days = interval_days
    rec.by_weekday = by_weekday
    rec.day_of_month = day_of_month
    rec.run_time_local = run_time_local
    rec.start_date = start_date
    rec.end_date = end_date 
    rec.save()
    return JsonResponse({"success": True, "message": "המשימה החוזרת עודכנה בהצלחה.", "data": MentorTaskRecurrenceUtils._serialize_recurrence(rec)})


@login_required
@require_http_methods(["DELETE", "POST"])
@transaction.atomic
def recurrence_delete(request, rec_id: int):
    """
    DELETE /mentor/recurrences/<rec_id>/delete/
    """
    mentor = request.user.mentor
    rec = MentorTaskRecurrenceUtils._mentor_get_recurrence_or_404(mentor, rec_id)
    rec.delete()
    return JsonResponse({"success": True, "message": "המשימה החוזרת נמחקה."})


@login_required
@require_GET
def recurrence_runs(request, rec_id: int):
    """
    GET /mentor/recurrences/<rec_id>/runs/?limit=20
    Returns latest audit rows from RecurringRun for transparency.
    """
    mentor = request.user.mentor
    rec = MentorTaskRecurrenceUtils._mentor_get_recurrence_or_404(mentor, rec_id)

    limit = MentorTaskRecurrenceUtils._int_or_none(request.GET.get("limit")) or 20
    runs_qs = (
        RecurringRun.objects
        .filter(task_template=rec.task)
        .order_by("-created_at")[:limit]
    )
    return JsonResponse({
        "success": True,
        "data": [MentorTaskRecurrenceUtils._serialize_run(r) for r in runs_qs]
    })
