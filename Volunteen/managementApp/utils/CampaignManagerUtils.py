from shopApp.models import Campaign, Shop
from teenApp.entities.task import Task
from datetime import date
from django.core.files.uploadedfile import InMemoryUploadedFile
from mentorApp.models import Mentor
from Volunteen.constants import CAMPAIGN_MENTOR_USERNAME

class CampaignManagerUtils:
    
    @staticmethod
    def get_campaign_mentor() -> Mentor:
        """
        Return (and lazily create, if missing) the virtual Mentor used to assign
        campaign tasks. Keeps real mentors’ stats clean.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user, _ = User.objects.get_or_create(username=CAMPAIGN_MENTOR_USERNAME,
                                            defaults={"email": "",
                                                    "is_active": False})
        mentor, _ = Mentor.objects.get_or_create(user=user)
        return mentor


    @staticmethod
    def create_campaign_from_wizard(step1, step2, new_tasks_data, mentor_user, banner_img=None):
        """
        Creates a Campaign from step1/2 session data and returns it.

        Args:
            step1 (dict): Basic campaign data
            step2 (dict): Task selection data (existing task IDs)
            new_tasks_data (list): New task dicts from formset
            banner_img: Optional uploaded file

        Returns:
            Campaign instance
        """
        campaign = Campaign.objects.create(
            shop=Shop.objects.get(id=step1["shop"]),
            title=step1["title"],
            description=step1.get("description", ""),
            banner_img=banner_img,
            start_date=date.fromisoformat(step1["start_date"]),
            end_date=date.fromisoformat(step1["end_date"]),
            max_children=int(step1.get("max_children", 0)),
            reward_title=step1.get("reward_title", ""),
            is_active=True
        )

        virtual_mentor = CampaignManagerUtils.get_campaign_mentor()

        # Link existing tasks
        selected_task_ids = step2.get("selected_task_ids", [])
        existing_tasks = Task.objects.filter(id__in=selected_task_ids)
        for task in existing_tasks:
            task.campaign = campaign
            task.assigned_mentors.add(virtual_mentor)
            task.save()

        # Create new tasks and assign mentor
        for task_data in new_tasks_data:
            new_task = Task.objects.create(
                title=task_data["title"],
                description=task_data["description"],
                deadline=date.fromisoformat(task_data["deadline"]),
                points=task_data["points"],
                proof_required=task_data.get("proof_required", False),
                img=task_data.get("img"),
                campaign=campaign,
                is_template=False
            )
            new_task.assigned_mentors.add(virtual_mentor)

        return campaign


    @staticmethod
    def serialize_task_data(cleaned_data):
        safe_data = {}
        for key, value in cleaned_data.items():
            if isinstance(value, (date, )):
                safe_data[key] = value.isoformat()
            else:
                safe_data[key] = value
        return safe_data
