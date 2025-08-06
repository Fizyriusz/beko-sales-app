from django import forms
from .models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            f.name
            for f in Task._meta.get_fields()
            if f.editable and not f.auto_created
        ]

    def clean(self):
        cleaned_data = super().clean()
        data_od = cleaned_data.get("data_od")
        data_do = cleaned_data.get("data_do")

        if data_od and data_do and data_do < data_od:
            raise forms.ValidationError(
                "Data zakończenia nie może być wcześniejsza niż data rozpoczęcia."
            )

        return cleaned_data
