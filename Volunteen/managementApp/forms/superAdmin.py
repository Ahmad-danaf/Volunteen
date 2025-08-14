from institutionApp.models import Institution
from django import forms
from mentorApp.models import Mentor
from teenApp.entities import TaskProofRequirement

class ProofBulkForm(forms.Form):
    institutions = forms.ModelMultipleChoiceField(
        queryset=Institution.objects.order_by("name"),
        required=False, label="מוסדות"
    )
    mentors = forms.ModelMultipleChoiceField(
        queryset=Mentor.objects.select_related("user").prefetch_related("institutions").order_by("user__username"),
        required=False, label="מנטורים נבחרים"
    )
    action = forms.ChoiceField(
        choices=[("add", "הוספה"), ("remove", "הסרה")],
        widget=forms.RadioSelect, label="פעולה"
    )
    proof_options = forms.MultipleChoiceField(
        choices=TaskProofRequirement.choices,
        required=False, label="אפשרויות הוכחה"
    )

