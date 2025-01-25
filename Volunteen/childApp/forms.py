from django import forms
from shopApp.models import Shop, Redemption

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