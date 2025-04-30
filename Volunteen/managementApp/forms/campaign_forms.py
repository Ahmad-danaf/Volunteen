from django import forms
from shopApp.models import Campaign, Shop
from teenApp.entities.task import Task

class CampaignStep1Form(forms.Form):
    title = forms.CharField(
        label="כותרת הקמפיין", 
        max_length=120, 
        widget=forms.TextInput(attrs={"class": "form-input w-full", "placeholder": "לדוגמה: קמפיין פתיחת Volunteen Market"})
    )

    description = forms.CharField(
        label="תיאור", 
        widget=forms.Textarea(attrs={"class": "form-textarea w-full", "rows": 4, "placeholder": "פרטים נוספים על הקמפיין"}), 
        required=False
    )

    banner_img = forms.ImageField(
        label="באנר", 
        required=False
    )

    start_date = forms.DateField(
        label="תאריך התחלה", 
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input w-full"})
    )

    end_date = forms.DateField(
        label="תאריך סיום", 
        widget=forms.DateInput(attrs={"type": "date", "class": "form-input w-full"})
    )

    max_children = forms.IntegerField(
        label="מספר ילדים מקסימלי (0 = ללא הגבלה)", 
        min_value=0, 
        widget=forms.NumberInput(attrs={"class": "form-input w-full"}), 
        initial=0
    )

    reward_title = forms.CharField(
        label="תיאור תגמול", 
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={"class": "form-input w-full", "placeholder": "לדוגמה: קופון 10%"})
    )
    
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(is_active=True),
        label="בחר חנות",
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("תאריך הסיום לא יכול להיות לפני תאריך ההתחלה.")
        
        return cleaned_data

class CampaignTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "deadline", "points", "proof_required"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input w-full", "placeholder": "כותרת המשימה"}),
            "description": forms.Textarea(attrs={"class": "form-textarea w-full", "rows": 3}),
            "deadline": forms.DateInput(attrs={"type": "date", "class": "form-input w-full"}),
            "points": forms.NumberInput(attrs={"class": "form-input w-full"}),
            "proof_required": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
