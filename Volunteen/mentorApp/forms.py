from django import forms
from teenApp.entities.task import Task,TimeWindowRule
from teenApp.entities import TaskProofRequirement
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
            'proof_requirement', 'send_whatsapp_on_assign'
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
            'proof_requirement': forms.Select(attrs={'class': 'form-select'}),
            'send_whatsapp_on_assign': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
            self.mentor = kwargs.pop('mentor', None)
            self.is_duplicate = kwargs.pop('is_duplicate', False)
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
            self.fields['proof_requirement'].help_text = (
            "בחר את סוג ההוכחה – חלק מהאפשרויות עשויות להיות חסומות לפי ההרשאות שלך."
            )
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
            self.fields['proof_requirement'].label = 'דרישת הוכחה'
            self.fields['send_whatsapp_on_assign'].label = 'שלח WhatsApp בעת ההקצאה'

            if self.mentor:
                self.fields['assigned_children'].queryset = self.mentor.children.all()
                
            # show only allowed choices for this mentor
            allowed = []
            for val, label in TaskProofRequirement.choices:
                if not self.mentor or self.mentor.can_use_proof_option(val):
                    allowed.append((val, label))

            # hard fallback: if somehow nothing remains, at least show base options
            if not allowed:
                allowed = [
                    (TaskProofRequirement.CAMERA_ONLY, TaskProofRequirement.CAMERA_ONLY.label),
                    (TaskProofRequirement.CAMERA_OR_GALLERY, TaskProofRequirement.CAMERA_OR_GALLERY.label),
                ]
            self.fields['proof_requirement'].choices = allowed
            
            self.lock_special = False 
            current_value = None
            if self.instance and getattr(self.instance, "pk", None):
                current_value = self.instance.proof_requirement

            if current_value and (self.mentor and not self.mentor.can_use_proof_option(current_value)):
                if current_value not in [v for v, _ in allowed]:
                    # prepend current choice so it's visible
                    label = dict(TaskProofRequirement.choices).get(current_value, current_value)
                    allowed = [(current_value, f"{label} (קיים במשימה)") ] + allowed
                self.lock_special = True

            self.fields['proof_requirement'].choices = allowed
            # When duplicating a task, allow editing key fields and reset the deadline.
            if self.is_duplicate:
                for field in ['title', 'description', 'points']:
                    self.fields[field].widget.attrs.pop('readonly', None)
                # Reset the deadline so the mentor must pick a new one
                self.initial['deadline'] = None
                
            if not self.initial.get('proof_requirement') and self.fields['proof_requirement'].choices:
                self.initial['proof_requirement'] = self.fields['proof_requirement'].choices[0][0]

    
    def clean_proof_requirement(self):
        val = self.cleaned_data['proof_requirement']
        if self.mentor and not self.mentor.can_use_proof_option(val):
            raise forms.ValidationError("אין לך הרשאה לבחור אפשרות זו.")
        return val
    
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