from django import forms
from teenApp.entities.task import Task
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from captcha.fields import CaptchaField
from django import forms
from teenApp.entities.task import Task
from Volunteen.constants import AVAILABLE_CITIES
from django import forms
from django.utils.translation import gettext_lazy as _

class RedemptionForm(forms.Form):
    points = forms.IntegerField(label=_('Points to Redeem'), min_value=1)




class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("מתאריך")
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("עד תאריך")
    )
    
class DateRangeCityForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("מתאריך")
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("עד תאריך")
    )
    city = forms.ChoiceField(
        choices=[('ALL', _('כל הערים'))] + AVAILABLE_CITIES,
        required=False,
        label=_('עיר')
    )
    
    
class CityDateRangeForm(forms.Form):
    DATE_RANGE_CHOICES = [
        ('current_month', _('חודש נוכחי')),
        ('last_month', _('חודש שעבר')),
        ('all_time', _('כל הזמנים')),
        ('custom', _('טווח מותאם')),
    ]

    date_range_selection = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        widget=forms.RadioSelect,  # or Select if preferred
        required=True,
        label=_('סנן לפי תאריך')
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("מתאריך")
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.TextInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("עד תאריך")
    )

    city = forms.ChoiceField(
        choices=[('ALL', _('כל הערים'))] + AVAILABLE_CITIES,
        required=False,
        label=_('עיר')
    )

    def clean(self):
        """
        Validate that if date_range_selection = 'custom',
        then both start_date and end_date are provided.
        """
        cleaned_data = super().clean()
        date_selection = cleaned_data.get('date_range_selection')

        if date_selection == 'custom':
            if not cleaned_data.get('start_date') or not cleaned_data.get('end_date'):
                self.add_error('start_date', _('חובה לציין תאריך התחלה וסיום.'))
                self.add_error('end_date', _('חובה לציין תאריך התחלה וסיום.'))

        return cleaned_data
