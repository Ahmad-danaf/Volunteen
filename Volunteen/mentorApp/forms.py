from django import forms
from teenApp.entities.task import Task,TimeWindowRule
from childApp.models import Child
from mentorApp.models import MentorGroup
from django.utils.translation import gettext_lazy as _
from mentorApp.utils.MentorUtils import MentorUtils
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_time, parse_date

HEBREW_WEEKDAYS = (
    (0, "שני"), (1, "שלישי"), (2, "רביעי"),
    (3, "חמישי"), (4, "שישי"), (5, "שבת"), (6, "ראשון"),
)

class TaskForm(forms.ModelForm):
    assigned_children = forms.ModelMultipleChoiceField(
        queryset=Child.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'points', 'deadline', 
            'img', 'additional_details', 'assigned_children', 'is_template', 'is_pinned',
            'proof_required', 'send_whatsapp_on_assign'
        ]       
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'img': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'additional_details': forms.Textarea(attrs={'class': 'form-control'}),
            'is_template': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'proof_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_whatsapp_on_assign': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
            # Accept extra flags to control duplication and template creation behavior
            self.mentor = kwargs.pop('mentor', None)
            self.is_duplicate = kwargs.pop('is_duplicate', False)
            # is_template flag is now just used to mark the task, not to modify field behavior
            self.is_template = kwargs.pop('is_template', False)
            super(TaskForm, self).__init__(*args, **kwargs)
            
            # Hebrew help text overrides
            self.fields['title'].help_text = 'הכנס את כותרת המשימה'
            self.fields['description'].help_text = 'תאר את המשימה בקצרה'
            self.fields['points'].help_text = 'מספר הנקודות שהמשימה שווה'
            self.fields['deadline'].help_text = 'בחר את מועד הסיום של המשימה'
            self.fields['img'].help_text = 'תמונה אופציונלית למשימה'
            self.fields['additional_details'].help_text = 'פרטים נוספים שתרצה לציין'
            self.fields['assigned_children'].help_text = 'בחר את הילדים שיקבלו את המשימה'
            self.fields['is_template'].help_text = 'סמן אם ברצונך לשמור כתבנית לשימוש עתידי'
            self.fields['is_pinned'].help_text = 'הפעל את האופציה אם ברצונך להעדיף משימה זו ולהציג אותה בצורה בולטת בראש הרשימה.'
            self.fields['proof_required'].help_text = 'אם מסומן, הילד יצטרך להעלות תמונת הוכחה (צ׳ק אין). אם לא, תתווסף תמונה אוטומטית.'
            self.fields['send_whatsapp_on_assign'].help_text = 'אם מסומן, תישלח הודעת WhatsApp כאשר מוקצת המשימה לילד'

            self.fields['title'].label = 'כותרת'
            self.fields['description'].label = 'תיאור'
            self.fields['points'].label = 'נקודות'
            self.fields['deadline'].label = 'מועד סיום'
            self.fields['img'].label = 'תמונה'
            self.fields['additional_details'].label = 'פרטים נוספים'
            self.fields['assigned_children'].label = 'הקצאת ילדים'
            self.fields['is_template'].label = 'שמור כתבנית'
            self.fields['is_pinned'].label = 'מועדפת'
            self.fields['proof_required'].label = 'עם תמונת הוכחה'
            self.fields['send_whatsapp_on_assign'].label = 'שלח WhatsApp בעת ההקצאה'

            if self.mentor:
                self.fields['assigned_children'].queryset = self.mentor.children.all()

            # When duplicating a task, allow editing key fields and reset the deadline.
            if self.is_duplicate:
                for field in ['title', 'description', 'points']:
                    self.fields[field].widget.attrs.pop('readonly', None)
                # Reset the deadline so the mentor must pick a new one
                self.initial['deadline'] = None
                

def validate_timewindow_payload(payload):
    """
    payload : list[dict] – each dict keys:
      window_type, specific_date, weekday, start_time, end_time
    returns the cleaned list (converted types) or raises ValidationError
    """
    if not isinstance(payload, list):
        raise ValidationError("פורמט חלונות הזמן אינו תקין")

    seen = {"check_in": 0, "check_out": 0}
    cleaned = []

    for row in payload:
        wt = row.get("window_type")
        if wt not in ("check_in", "check_out"):
            raise ValidationError("סוג חלון זמן לא תקין")
        seen[wt] += 1
        if seen[wt] > 1:
            raise ValidationError("ניתן להגדיר חלון אחד בלבד לכל סוג (צ'ק-אין / צ'ק-אאוט)")

        sd  = parse_date( row.get("specific_date") ) if row.get("specific_date") else None
        wd  = row.get("weekday")
        wd  = int(wd) if wd not in (None,"") else None
        st  = parse_time( row.get("start_time") ) if row.get("start_time") else None
        et  = parse_time( row.get("end_time") ) if row.get("end_time") else None

        # row completely empty? skip
        if not any([sd, wd, st, et]):
            continue

        # mutual exclusivity
        if sd and wd:
            raise ValidationError("בחר או תאריך ספציפי או יום בשבוע – לא את שניהם.")

        if not (st and et):
            raise ValidationError("יש למלא גם שעת התחלה וגם שעת סיום.")

        if st >= et:
            raise ValidationError("שעת הסיום חייבת להיות אחרי שעת ההתחלה.")

        cleaned.append({
            "window_type": wt,
            "specific_date": sd,
            "weekday": wd,
            "start_time": st,
            "end_time": et,
        })

    return cleaned


class TaskImageForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['img']
        
class BonusPointsForm(forms.Form):
    task = forms.ModelChoiceField(queryset=Task.objects.none(), label="Select Task")
    child = forms.ModelChoiceField(queryset=Child.objects.none(), label="Select Child")
    bonus_points = forms.IntegerField(label="Bonus Points", min_value=1, max_value=10)

    def __init__(self, mentor=None, *args, **kwargs):
        super(BonusPointsForm, self).__init__(*args, **kwargs)
        if mentor:
            self.fields['task'].queryset = Task.objects.filter(assigned_mentors=mentor)
            self.fields['child'].queryset = Child.objects.filter(mentors=mentor)
            
            
            
class MentorGroupForm(forms.ModelForm):
    class Meta:
        model = MentorGroup
        fields = ['name', 'children', 'description', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'שם הקבוצה'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'תיאור הקבוצה', 'rows': 3}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'children': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': _('שם הקבוצה'),
            'children': _('ילדים בקבוצה'),
            'description': _('תיאור'),
            'color': _('צבע'),
        }

    def __init__(self, *args, mentor=None, **kwargs):
        """
        Initialize form with filtered children based on mentor.
        """
        super().__init__(*args, **kwargs)
        if mentor:
            self.fields['children'].queryset = MentorUtils.get_children_for_mentor(mentor)