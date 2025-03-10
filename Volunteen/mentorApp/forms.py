from django import forms
from teenApp.entities.task import Task
from childApp.models import Child

class TaskForm(forms.ModelForm):
    assigned_children = forms.ModelMultipleChoiceField(
        queryset=Child.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    

    class Meta:
        model = Task
        fields = ['title', 'description', 'points', 'deadline', 'img', 'additional_details', 'assigned_children']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'img': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
            'additional_details': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.mentor = kwargs.pop('mentor', None)
        super(TaskForm, self).__init__(*args, **kwargs)
        if self.mentor:
            self.fields['assigned_children'].queryset = self.mentor.children.all()

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