from django import forms
from teenApp.entities.task import Task
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from captcha.fields import CaptchaField
from django import forms
from teenApp.entities.task import Task

from django import forms


class CreateUserForm(UserCreationForm):
    captcha = CaptchaField()
    phone = forms.CharField(max_length=10, required=False, help_text='Enter a valid phone number.')

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password1', 'password2']

    def save(self, commit=True):
        user = super(CreateUserForm, self).save(commit=False)
        user.phone = self.cleaned_data['phone']
        if commit:
            user.save()
        return user




class RedemptionForm(forms.Form):
    points = forms.IntegerField(label='Points to Redeem', min_value=1)

        


class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='תאריך התחלה')
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='תאריך סיום')


