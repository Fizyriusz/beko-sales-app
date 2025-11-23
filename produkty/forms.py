from django import forms
from .models import Task, Zadanie

class TaskForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        produkty_queryset = kwargs.pop('produkty_queryset', None)
        super(TaskForm, self).__init__(*args, **kwargs)
        if produkty_queryset is not None:
            self.fields['produkty'].queryset = produkty_queryset

    class Meta:
        model = Task
        fields = [
            'nazwa', 'data_od', 'data_do', 'opis', 'produkty',
            'prog_ilosc_1', 'prog_premia_1', 'prog_ilosc_2', 'prog_premia_2'
        ]
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'data_od': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_do': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produkty': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
            'prog_ilosc_1': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_premia_1': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_ilosc_2': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_premia_2': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_od = cleaned_data.get('data_od')
        data_do = cleaned_data.get('data_do')
        produkty = cleaned_data.get('produkty')

        if data_od and data_do and data_do < data_od:
            raise forms.ValidationError("Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        if not produkty:
            self.add_error('produkty', 'Produkty są wymagane dla tego typu zadania.')

        return cleaned_data


class ZadanieForm(forms.ModelForm):
    class Meta:
        model = Zadanie
        fields = [
            'nazwa', 'data_start', 'data_koniec', 'produkty',
            'target', 'prog_1', 'prog_1_premia', 'prog_2', 'prog_2_premia'
        ]
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'data_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_koniec': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'produkty': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
            'target': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_1': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_1_premia': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_2': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_2_premia': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_start = cleaned_data.get('data_start')
        data_koniec = cleaned_data.get('data_koniec')

        if data_start and data_koniec and data_koniec < data_start:
            raise forms.ValidationError("Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        return cleaned_data
