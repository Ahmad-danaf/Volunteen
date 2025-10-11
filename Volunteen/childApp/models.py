from datetime import timedelta
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, Group
from Volunteen.constants import AVAILABLE_CITIES
from childApp.utils.child_level_management import calculate_total_points
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class Medal(models.Model):
    name = models.CharField(max_length=255, verbose_name='Medal Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    points_reward = models.IntegerField(default=0, verbose_name='Points Reward')
    criterion = models.CharField(max_length=255, verbose_name='Criterion Function')  # קריטריון לזכייה במדליה

    def __str__(self):
        return self.name


class Child(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='User')
    mentors = models.ManyToManyField("mentorApp.Mentor", related_name='children', blank=True, verbose_name='Mentors')
    points = models.IntegerField(default=0, verbose_name='Points')
    completed_tasks = models.ManyToManyField('teenApp.Task', related_name='completed_by_children', blank=True, verbose_name='Completed Tasks')
    identifier = models.CharField(max_length=5, unique=True, verbose_name='Identifier')
    secret_code = models.CharField(max_length=3, verbose_name='Secret Code')
    institution = models.ForeignKey("institutionApp.Institution", on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='Institution')
    parent = models.ForeignKey('parentApp.Parent', on_delete=models.SET_NULL, null=True, blank=True, related_name='children', verbose_name='Parent')
    medals = models.ManyToManyField(Medal, blank=True, verbose_name='Medals')
    streak_count = models.IntegerField(default=0, verbose_name="Streak Count")
    last_streak_date = models.DateField(null=True, blank=True, verbose_name="Last Streak Date")
    last_level_awarded = models.IntegerField(default=1, verbose_name="Last Level Awarded")
    city = models.CharField(
        max_length=3,
        choices=AVAILABLE_CITIES,
        verbose_name="City",
        blank=True,
        null=True,
    )
    campaign_ban_until = models.DateTimeField(null=True, blank=True)
    is_temp_user = models.BooleanField(default=False)
    trial_end = models.DateField(null=True, blank=True)
    @property
    def level(self):
        return (calculate_total_points(self) // 100) + 1
    
    @property
    def phone_number(self):
        return self.user.personal_info.phone_number if hasattr(self.user, 'personal_info') else None
    
    def has_active_trial(self) -> bool:
        return self.trial_end and self.trial_end >= timezone.now().date()
    
    def start_trial(self, days: int = 7) -> bool:
        """
        Start a trial if not already active. 
        Returns True if started, False if already had one.
        """
        if self.trial_end:
            return False
        from managementApp.utils.CampaignManagerUtils import CampaignManagerUtils
        from childApp.utils.campaign.TempUserCampaignUtils import TempUserCampaignUtils
        from teenApp.utils.NotificationManager import NotificationManager
        
        self.trial_end = timezone.now().date() + timedelta(days=days)
        campaign_mentor = CampaignManagerUtils.get_campaign_mentor()
        self.mentors.clear()
        self.mentors.add(campaign_mentor)
        campaign_institution = CampaignManagerUtils.get_campaign_institution()
        self.institution = campaign_institution
        self.save(update_fields=["trial_end", "institution"])
        
        WELCOME_BACK_TRIAL_CHILD_MSG = """🔥 رجعت لعالم Volunteen من جديد! 🧡✨
            جاهز تبدأ رحلة جديدة مليانة تحديات، جوائز 🎁، وإنجازات 💪

            معانا الخير ممتع أكتر 😋
            يلا اجمع TeenCoins 💰 وخلّي كل يوم قصة نجاح جديدة 🚀

            🏠 صفحتك الشخصية: https://www.volunteen.site/child/home/

            📸 تابعونا عالإنستا: https://rb.gy/9i3yxf

            👇 انضموا لجروب الواتساب: http://bit.ly/484hQf1
            """
        if self.phone_number:
            NotificationManager.sent_whatsapp(
                WELCOME_BACK_TRIAL_CHILD_MSG,
                self.phone_number
            )
        try:
            from mentorApp.models import MentorGroup
            DEFAULT_MENTOR_CAMPAIGN_GROUP_NAME = "משתמשים חוזרים"
            mentor_group = MentorGroup.objects.filter(
                name=DEFAULT_MENTOR_CAMPAIGN_GROUP_NAME,
                mentor=campaign_mentor,
            ).first()
            if mentor_group:
                mentor_group.children.add(self)
        except Exception as e:
            pass
        TempUserCampaignUtils.enqueue_assign_live_tasks(self.id, campaign_mentor.user.id)
        return True
    
    def has_trial_ended(self) -> bool:
        return self.trial_end and self.trial_end < timezone.now().date()

    def add_points(self, points):
        """
        Add points to the child and save changes.
        """
        self.points += points
        self.save()

    
    def subtract_points(self, points):
        """
        Subtract points from the child if there are enough points.
        """
        if self.points >= points:
            self.points -= points
            self.save()
        else:
            raise ValueError("Not enough points to subtract")

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        """
        Automatically add the child to the 'Children' group if not already added.
        """
        super().save(*args, **kwargs)
        children_group, created = Group.objects.get_or_create(name='Children')
        self.user.groups.add(children_group)


class ChildReferral(models.Model):
    referred_child = models.ForeignKey(
        "childApp.Child",
        on_delete=models.CASCADE,
        related_name="referrals_received",
        db_index=True,
    )
    referrer = models.ForeignKey(
        "childApp.Child",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="referrals_made",
        db_index=True,
    )
    rewarded_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reward_amount = models.IntegerField(default=0)
    trial_extended_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Child Referral"
        verbose_name_plural = "Child Referrals"
        constraints = [
            models.UniqueConstraint(
                fields=["referred_child"], name="unique_referral_per_child"
            )
        ]
        indexes = [
            models.Index(fields=["referrer", "created_at"], name="ref_by_date_idx"),
        ]

    def __str__(self):
        return f"{self.referred_child} referred by {self.referrer or 'unknown'}"

class StreakMilestoneAchieved(models.Model):
    """
    Records that a child has reached a specific streak milestone (e.g., 10, 20, 30 days).
    Ensures each milestone is only rewarded once per child.
    """
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name='streak_milestones',
        verbose_name=_("Child"),
    )
    streak_day = models.PositiveIntegerField(
        verbose_name=_("Streak Day"),
        help_text=_("Streak count at which this milestone was achieved."),
    )
    achieved_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Achieved At"),
    )

    class Meta:
        verbose_name = _("Streak Milestone Achieved")
        verbose_name_plural = _("Streak Milestones Achieved")
        unique_together = ("child", "streak_day")
        ordering = ['-achieved_at']

    def __str__(self):
        return f"{self.child.user.username} - {self.streak_day} days"
    
    
class BanScope(models.TextChoices):
    PURCHASE = "purchase", "Shop purchases"
    CAMPAIGN = "campaign", "Campaign join/benefits"
    ALL      = "all", "All restricted actions"
    
DEFAULT_BAN_NOTES = {
    BanScope.PURCHASE: "החשבון שלך כרגע חסום לביצוע רכישות",
    BanScope.CAMPAIGN: "החשבון שלך כרגע חסום מהשתתפות בקמפיינים",
    BanScope.ALL: "החשבון שלך חסום לפעולה זו",
}

class ChildBan(models.Model):
    child       = models.ForeignKey("childApp.Child", on_delete=models.CASCADE, related_name="ban_records")
    scope       = models.CharField(max_length=24, choices=BanScope.choices, default=BanScope.PURCHASE)
    starts_at   = models.DateTimeField(default=timezone.now)
    ends_at     = models.DateTimeField(null=True, blank=True)  # null = indefinite
    # Visible to child/parent (keep short).
    note_child  = models.CharField(max_length=140, blank=True,default=DEFAULT_BAN_NOTES[BanScope.PURCHASE])
    # Internal note for staff/superadmin
    note_staff  = models.TextField(blank=True)
    severity    = models.CharField(max_length=16, default="hard")    # soft/hard
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="bans_created")
    created_at  = models.DateTimeField(auto_now_add=True)
    revoked_at  = models.DateTimeField(null=True, blank=True)
    revoked_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="bans_revoked"
    )
    revoke_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["child", "scope"]),
            models.Index(fields=["ends_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"Ban({self.child_id}, {self.scope}, {status})"

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("ends_at must be after starts_at.")