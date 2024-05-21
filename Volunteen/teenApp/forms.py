from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Task

from captcha.fields import CaptchaField

class CreateUserForm(UserCreationForm):
    # Form to create a new user with captcha verification
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

class TaskImageForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['img']

class IdentifyChildForm(forms.Form):
    # Form to identify a child using an identifier and secret code
    identifier = forms.CharField(max_length=5, label='Child Identifier')
    secret_code = forms.CharField(max_length=3, label='Secret Code', widget=forms.PasswordInput())

class RedemptionForm(forms.Form):
    # Form to redeem points
    points = forms.IntegerField(label='Points to Redeem', min_value=1)
