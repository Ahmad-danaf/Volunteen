from django import forms
from teenApp.entities.task import Task
from childApp.models import Child
from mentorApp.models import MentorGroup
from django.utils.translation import gettext_lazy as _

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
            'img', 'additional_details', 'assigned_children', 'is_template'
        ]       
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'img': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'additional_details': forms.Textarea(attrs={'class': 'form-control'}),
            'is_template': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
            # Accept extra flags to control duplication and template creation behavior
            self.mentor = kwargs.pop('mentor', None)
            self.is_duplicate = kwargs.pop('is_duplicate', False)
            # is_template flag is now just used to mark the task, not to modify field behavior
            self.is_template = kwargs.pop('is_template', False)
            super(TaskForm, self).__init__(*args, **kwargs)

            if self.mentor:
                self.fields['assigned_children'].queryset = self.mentor.children.all()

            # When duplicating a task, allow editing key fields and reset the deadline.
            if self.is_duplicate:
                for field in ['title', 'description', 'points']:
                    self.fields[field].widget.attrs.pop('readonly', None)
                # Reset the deadline so the mentor must pick a new one
                self.initial['deadline'] = None

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