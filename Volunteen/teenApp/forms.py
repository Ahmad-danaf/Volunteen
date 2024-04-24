from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Task

from captcha.fields import CaptchaField

class CreateUserForm(UserCreationForm):
    captcha = CaptchaField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']



class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title','description', 'deadline','img','points','duration','additional_details']

class UpdateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title','description', 'deadline','img','points', 'duration','additional_details']
