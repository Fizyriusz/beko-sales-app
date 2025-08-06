from django import forms
from .models import Task

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        data_od = cleaned_data.get('data_od')
        data_do = cleaned_data.get('data_do')
        typ = cleaned_data.get('typ')
        prog_mix = cleaned_data.get('prog_mix')
        mnoznik_mix = cleaned_data.get('mnoznik_mix')

        if data_od and data_do and data_do < data_od:
            raise forms.ValidationError("Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        if typ in [Task.Typ.MIX_PROWIZJA, Task.Typ.MIX_MNOZNIK] and prog_mix is None:
            self.add_error('prog_mix', 'Próg jest wymagany dla zadań typu mix.')

        if typ == Task.Typ.MIX_MNOZNIK and mnoznik_mix is None:
            self.add_error('mnoznik_mix', 'Mnożnik jest wymagany dla zadań typu mix mnożnik.')

        return cleaned_data
