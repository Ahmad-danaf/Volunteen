from django import forms
from managementApp.models import DonationCategory
class SimulateSpendForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=DonationCategory.objects.all(),
        label="בחר קטגוריה",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    amount = forms.IntegerField(
        min_value=1,
        label="כמות לדימוי",
        widget=forms.NumberInput(attrs={'class': 'form-input'})
    )
