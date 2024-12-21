from django import forms


class IdentifyChildForm(forms.Form):
    identifier = forms.CharField(max_length=5, label='מספר מזהה')
    secret_code = forms.CharField(max_length=3, label='קוד סודי', widget=forms.PasswordInput())
