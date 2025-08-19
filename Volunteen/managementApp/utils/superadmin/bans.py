# managementApp/utils/bans.py
from __future__ import annotations
from collections import defaultdict
from datetime import timedelta
from typing import List, Dict, Any, Iterable, Tuple,Optional

from django.db.models import Q
from django.utils import timezone

from childApp.models import Child,ChildBan,DEFAULT_BAN_NOTES,BanScope

def compute_end_from_preset(preset: str, starts_at):
    preset = (preset or "").strip()
    if not preset:
        return None
    if preset == "indefinite":
        return None
    if preset == "eod_il":
        local = timezone.localtime(starts_at)
        end_local = local.replace(hour=23, minute=59, second=59, microsecond=0)
        return timezone.make_aware(end_local.replace(tzinfo=None)) if timezone.is_naive(end_local) else end_local
    try:
        days = int(preset)
        return starts_at + timezone.timedelta(days=days)
    except Exception:
        return None

class BanQueryUtils:
    """Query + shaping helpers (no DTOs)."""

    @staticmethod
    def now():
        return timezone.now()

    @staticmethod
    def active_bans_qs(at=None):
        """
        Active = not revoked, started, and (no end or end in future).
        Returns a single QuerySet (no unions).
        """
        now = at or timezone.now()
        return (
            ChildBan.objects
            .select_related("child", "child__user", "created_by", "revoked_by")
            .filter(
                revoked_at__isnull=True,
                starts_at__lte=now,
            )
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        )

    @staticmethod
    def all_bans_qs():
        return ChildBan.objects.select_related("child", "child__user")

    @staticmethod
    def list_active_bans(at=None) -> List[ChildBan]:
        """Materialize active bans once."""
        return list(BanQueryUtils.active_bans_qs(at=at))

    @staticmethod
    def children_with_active_bans(at=None) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts:
        [
          {
            "child": <Child>,
            "active_bans": [
                {"id": int, "scope": str, "starts_at": dt, "ends_at": dt|None,
                 "note_child": str, "severity": str}
            ],
            "active_scopes": ["purchase", "campaign", ...],
            "total_active_scopes": 2
          },
          ...
        ]
        """
        now = at or timezone.now()
        bans = BanQueryUtils.list_active_bans(at=now)

        per_child_raw: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        child_ids = set()

        for b in bans:
            child_ids.add(b.child_id)
            per_child_raw[b.child_id].append({
                "id": b.id,
                "scope": b.scope,
                "starts_at": b.starts_at,
                "ends_at": b.ends_at,
                "note_child": b.note_child,
                "severity": b.severity,
            })

        if not child_ids:
            return []

        child_map = {
            c.id: c
            for c in Child.objects.select_related("user").filter(id__in=child_ids)
        }

        rows: List[Dict[str, Any]] = []
        for cid, items in per_child_raw.items():
            scopes = sorted({i["scope"] for i in items})
            items.sort(key=lambda x: x["starts_at"], reverse=True)
            rows.append({
                "child": child_map.get(cid),
                "active_bans": items,
                "active_scopes": scopes,
                "total_active_scopes": len(scopes),
            })

        # Sort: by number of active scopes, then by most recent ban start
        rows.sort(
            key=lambda r: (
                r["total_active_scopes"],
                (r["active_bans"][0]["starts_at"] if r["active_bans"] else timezone.make_aware(timezone.datetime.min))
            ),
            reverse=True,
        )
        return rows


class BanAnalytics:
    """
    Leaderboards/metrics without DTOs:
    - total ban days per child (open-ended counted until now)
    - total bans count per child
    Returns plain tuples for easy table usage.
    """

    @staticmethod
    def _ban_duration_days(ban: ChildBan, at=None) -> float:
        now = at or timezone.now()
        upper = ban.revoked_at or ban.ends_at or now
        if upper < ban.starts_at:
            return 0.0
        delta: timedelta = upper - ban.starts_at
        return max(delta.total_seconds() / 86400.0, 0.0)

    @staticmethod
    def child_totals(at=None) -> Dict[int, Dict[str, float]]:
        out: Dict[int, Dict[str, float]] = defaultdict(lambda: {"total_days": 0.0, "bans_count": 0})
        now = at or timezone.now()
        for ban in BanQueryUtils.all_bans_qs().only("id", "child_id", "starts_at", "ends_at", "revoked_at"):
            out[ban.child_id]["bans_count"] += 1
            out[ban.child_id]["total_days"] += BanAnalytics._ban_duration_days(ban, at=now)
        return out

    @staticmethod
    def top_by_total_days(limit=10, at=None) -> List[Tuple[Child, float, int]]:
        totals = BanAnalytics.child_totals(at=at)
        if not totals:
            return []
        child_ids = list(totals.keys())
        child_map = {
            c.id: c for c in Child.objects.select_related("user").filter(id__in=child_ids)
        }
        rows: List[Tuple[Child, float, int]] = []
        for cid, agg in totals.items():
            child = child_map.get(cid)
            if child:
                rows.append((child, agg["total_days"], int(agg["bans_count"])))
        rows.sort(key=lambda r: (r[1], r[2]), reverse=True)
        return rows[:limit]

    @staticmethod
    def top_by_bans_count(limit=10, at=None) -> List[Tuple[Child, int, float]]:
        totals = BanAnalytics.child_totals(at=at)
        if not totals:
            return []
        child_ids = list(totals.keys())
        child_map = {
            c.id: c for c in Child.objects.select_related("user").filter(id__in=child_ids)
        }
        rows: List[Tuple[Child, int, float]] = []
        for cid, agg in totals.items():
            child = child_map.get(cid)
            if child:
                rows.append((child, int(agg["bans_count"]), agg["total_days"]))
        rows.sort(key=lambda r: (r[1], r[2]), reverse=True)
        return rows[:limit]

def prepare_mentor_data(mentors_qs) -> List[Dict[str, Any]]:
    """Converts Mentor queryset (with user/children/institutions prefetched) to JSON-serializable list."""
    out: List[Dict[str, Any]] = []
    for m in mentors_qs:
        out.append({
            "id": m.id,
            "username": m.user.username,
            "full_name": f"{m.user.first_name or ''} {m.user.last_name or ''}".strip(),
            "institutions": [i.name for i in m.institutions.all()],
            "children": [
                {
                    "id": c.id,
                    "username": c.user.username,
                    "full_name": f"{c.user.first_name or ''} {c.user.last_name or ''}".strip(),
                    "identifier": c.identifier,
                }
                for c in m.children.all().select_related("user")
            ],
        })
    return out


def prepare_child_data(children_qs) -> List[Dict[str, Any]]:
    """Converts Child queryset (with user/institution selected) to JSON-serializable list."""
    return [
        {
            "id": c.id,
            "username": c.user.username,
        }
        for c in children_qs
    ]


def compute_end_from_preset(preset: str, starts_at) -> Optional[timezone.datetime]:
    """Maps UI preset -> ends_at (aware). Supports: 1/3/7/14/30, 'eod_il', 'indefinite'."""
    p = (preset or "").strip()
    if not p or p == "indefinite":
        return None
    if p == "eod_il":
        local = timezone.localtime(starts_at)
        end_local = local.replace(hour=23, minute=59, second=59, microsecond=0)
        return timezone.make_aware(end_local.replace(tzinfo=None)) if timezone.is_naive(end_local) else end_local
    try:
        days = int(p)
        return starts_at + timezone.timedelta(days=days)
    except Exception:
        return None


def default_note_for_scope(scope: str) -> str:
    """Returns child-facing default note by scope."""
    return DEFAULT_BAN_NOTES.get(scope, DEFAULT_BAN_NOTES.get(BanScope.ALL, ""))