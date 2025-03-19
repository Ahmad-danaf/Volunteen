from django import forms
from shopApp.models import Shop, Redemption
from managementApp.models import DonationCategory
class RedemptionRatingForm(forms.ModelForm):
    class Meta:
        model = Redemption
        fields = ['service_rating', 'reward_rating', 'notes']  # Add the notes field
        widgets = {
            'service_rating': forms.RadioSelect(choices=[(i, '') for i in range(1, 6)], attrs={'class': 'rating-icons'}),
            'reward_rating': forms.RadioSelect(choices=[(i, '') for i in range(1, 6)], attrs={'class': 'rating-icons'}),
            'notes': forms.Textarea(attrs={'placeholder': 'יש לך הערות? כתוב כאן...', 'rows': 4, 'class': 'form-control'}),
        }
        labels = {
            'service_rating': 'דרג את השירות',
            'reward_rating': 'דרג את הפרס',
            'notes': 'הערות נוספות (אופציונלי)',
        }
        
        
        
class DonationForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=DonationCategory.objects.filter(is_active=True),
        empty_label=None,
        label="קטגוריה לתרומה",
        widget=forms.Select(attrs={'class': 'form-control donation-category'})
    )
    amount = forms.IntegerField(
        min_value=1,
        label="כמות טינקוינס לתרומה",
        widget=forms.NumberInput(attrs={'class': 'form-control donation-amount', 'placeholder': 'הזן כמות...'})
    )
    note = forms.CharField(
        required=False,
        label="הערה (לא חובה)",
        widget=forms.Textarea(attrs={'class': 'form-control donation-note', 'rows': 3, 'placeholder': 'הוסף הערה אישית...'})
    )