import csv
import io
from random import randint
from typing import List, Dict, Tuple, Optional
from django.contrib.auth.models import User
from childApp.models import Child
from mentorApp.models import Mentor
from institutionApp.models import Institution
from parentApp.models import ChildSubscription
from django.db import transaction
import datetime
from django.utils import timezone

def _parse_date(date_str: str) -> Optional[datetime.date]:
    """
    Accepts 'MM/DD/YYYY' and returns date object (or None if blank).
    """
    if not date_str:
        return None
    return datetime.datetime.strptime(date_str, "%m/%d/%Y").date()


class SuperAdminUtility:
    @staticmethod
    def get_next_free_identifier() -> str:
        """
        Finds the first available 5-digit identifier that is not already used.
        Returns a string like "00001".
        """
        from childApp.models import Child

        used_ids = set(
            Child.objects.values_list("identifier", flat=True)
            .filter(identifier__regex=r"^\d{5}$")  # Only check valid 5-digit strings
        )

        for i in range(1, 99999):  # Max: "99999"
            candidate = str(i).zfill(5)
            if candidate not in used_ids:
                return candidate

        raise ValueError("No available identifier found under 99999.")


    @staticmethod
    def generate_secret_code() -> str:
        """
        Generate a random 3-digit secret code.
        """
        return str(randint(100, 999))

    @staticmethod
    def parse_csv(file) -> List[Dict[str, str]]:
        """
        Parse uploaded CSV file (InMemoryUploadedFile or path), return list of rows.
        """
        decoded = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        return list(reader)

    @staticmethod
    @transaction.atomic
    def create_child_from_row(row: Dict[str, str]) -> Tuple[bool, Dict]:
        log = {
            "username": row.get("username", "").strip(),
            "status": "✅ Success",
            "warnings": [],
            "errors": [],
        }

        try:
            # Extract + validate basics 
            username = row.get("username", "").strip()
            password = row.get("password", "").strip()
            if not username or not password:
                raise ValueError("Username and password are required.")

            raw_id = row.get("identifier", "").strip()
            identifier = raw_id.zfill(5) if raw_id else SuperAdminUtility.get_next_free_identifier()
            secret_code = (row.get("secret_code", "").strip()
                        or SuperAdminUtility.generate_secret_code())
            mentor_un = row.get("mentor", "").strip()
            inst_name = row.get("institution", "").strip()
            city      = row.get("city", "").strip() or "TLV"

            log["used_identifier"] = identifier

            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={"email": "", "first_name": "", "last_name": ""}
            )
            if user_created:
                user.set_password(password)
                user.save()
                log["created_user"] = True
            else:
                log["created_user"] = False
                log["warnings"].append("User exists – continuing to child creation.")
                

            # Institution & Child
            institution = Institution.objects.filter(name=inst_name).first() if inst_name else None
            if not institution:
                log["warnings"].append(f"Institution '{inst_name}' not found/empty.")
            child, child_created = Child.objects.get_or_create(
                user=user,
                defaults={
                    "identifier": identifier,
                    "secret_code": secret_code,
                    "institution": institution,
                    "city": city,
                },
            )
            if not child_created:
                log["status"] = "⚠️ Skipped (Child Exists)"

            # Mentor link 
            if mentor_un:
                mentor = Mentor.objects.filter(user__username=mentor_un).first()
                if mentor:
                    child.mentors.add(mentor)
                else:
                    log["warnings"].append(f"Mentor '{mentor_un}' not found.")
            else:
                log["warnings"].append("mentor column missing.")

            # Subscription (all five cols must be present) 
            sub_cols = ["payment_method", "plan", "start_date", "end_date", "auto_renew"]
            if all(row.get(c, "").strip() for c in sub_cols):
                plan = row["plan"].strip().upper()
                pay_method = row["payment_method"].strip().upper()
                start_date = _parse_date(row["start_date"].strip())
                end_date = _parse_date(row["end_date"].strip())
                auto_renew = row["auto_renew"].strip().upper() in ["TRUE", "YES", "1"]

                if plan not in ChildSubscription.Plan.values:
                    raise ValueError(f"Invalid plan '{plan}'")
                if pay_method not in ChildSubscription.PaymentMethod.values:
                    raise ValueError(f"Invalid payment_method '{pay_method}'")
                if not start_date:
                    raise ValueError("start_date missing or invalid.")

                if not end_date:
                    end_date = start_date + (datetime.timedelta(days=30)
                                            if plan == "MONTHLY"
                                            else datetime.timedelta(days=365))

                sub, created_sub = ChildSubscription.objects.update_or_create(
                    child=child,
                    defaults={
                        "payment_method": pay_method,
                        "plan": plan,
                        "start_date": start_date,
                        "end_date": end_date,
                        "auto_renew": auto_renew,
                        "status": ChildSubscription.Status.ACTIVE,
                        "updated_at": timezone.now(),
                        "notes": "Imported via CSV SuperAdmin upload",
                    })
                log["subscription_action"] = "Created" if created_sub else "Updated"
            else:
                log["subscription_action"] = "Not provided"

            return (log["status"].startswith("✅"), log)

        except Exception as e:
            log["status"] = "❌ Error"
            log["errors"].append(str(e))
            return False, log
