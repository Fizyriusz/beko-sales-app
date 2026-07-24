from django import forms
from .models import Zadanie, Produkt

class ZadanieForm(forms.ModelForm):
    class Meta:
        model = Zadanie
        fields = [
            'nazwa', 'opis', 'produkty', 'data_start', 'data_koniec',
            'target', 'prog_1', 'prog_1_premia', 'prog_2', 'prog_2_premia',
            'mnoznik_mix', 'prog_mix', 'typ'
        ]
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produkty': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
            'data_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_koniec': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'target': forms.Select(attrs={'class': 'form-control'}),
            'prog_1': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_1_premia': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_2': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_2_premia': forms.NumberInput(attrs={'class': 'form-control'}),
            'mnoznik_mix': forms.NumberInput(attrs={'class': 'form-control'}),
            'prog_mix': forms.NumberInput(attrs={'class': 'form-control'}),
            'typ': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        data_start = cleaned_data.get('data_start')
        data_koniec = cleaned_data.get('data_koniec')

        if data_start and data_koniec and data_koniec < data_start:
            raise forms.ValidationError("Data zakończenia nie może być wcześniejsza niż data rozpoczęcia.")

        # Walidacja pol zaleznie od typu zadania - zapobiega zapisaniu zadania
        # bez danych potrzebnych do naliczenia premii/mnoznika.
        typ = cleaned_data.get('typ')
        if typ == Zadanie.Typ.MIX_MNOZNIK:
            if cleaned_data.get('mnoznik_mix') is None:
                self.add_error('mnoznik_mix', "Zadanie typu 'Mix mnożnik' wymaga podania mnożnika.")
            if cleaned_data.get('prog_mix') is None:
                self.add_error('prog_mix', "Zadanie typu 'Mix mnożnik' wymaga podania progu.")
        elif typ == Zadanie.Typ.MIX_PROWIZJA:
            if cleaned_data.get('prog_mix') is None:
                self.add_error('prog_mix', "Zadanie typu 'Mix prowizja' wymaga podania progu.")
            if cleaned_data.get('prog_1_premia') is None and cleaned_data.get('prog_2_premia') is None:
                self.add_error(None, "Zadanie typu 'Mix prowizja' wymaga podania co najmniej jednej premii progowej.")
        elif typ == Zadanie.Typ.KONKRETNE_MODELE:
            if cleaned_data.get('prog_1') is None:
                self.add_error('prog_1', "Zadanie typu 'Konkretne modele' wymaga podania progu.")

        return cleaned_data


class ProduktForm(forms.ModelForm):
    class Meta:
        model = Produkt
        fields = ['model', 'marka', 'grupa_towarowa', 'stawka']
        widgets = {
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'marka': forms.TextInput(attrs={'class': 'form-control'}),
            'grupa_towarowa': forms.TextInput(attrs={'class': 'form-control'}),
            'stawka': forms.NumberInput(attrs={'class': 'form-control'}),
        }

from django.contrib.auth.models import User
from .models import Funkcja, Podpowiedz

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Hasło")
    
    class Meta:
        model = User
        fields = ['username', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Login (Nazwa użytkownika)'
        }
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Login (Nazwa użytkownika)'
        }

class FunkcjaForm(forms.ModelForm):
    class Meta:
        model = Funkcja
        fields = ['nazwa', 'opis', 'produkty']
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'produkty': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        }

class PodpowiedzForm(forms.ModelForm):
    class Meta:
        model = Podpowiedz
        fields = ['tytul', 'tresc']
        widgets = {
            'tytul': forms.TextInput(attrs={'class': 'form-control'}),
            'tresc': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
        }
