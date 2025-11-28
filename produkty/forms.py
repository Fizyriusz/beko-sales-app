from django import forms
from .models import Zadanie

class ZadanieForm(forms.ModelForm):
    class Meta:
        model = Zadanie
        fields = [
            'nazwa', 'opis', 'produkty', 'data_start', 'data_koniec',
            'prog_1', 'prog_2'
        ]
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produkty': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
            'data_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_koniec': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prog_1': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_2': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_start = cleaned_data.get('data_start')
        data_koniec = cleaned_data.get('data_koniec')

        if data_start and data_koniec and data_koniec < data_start:
            raise forms.ValidationError("Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        return cleaned_data
