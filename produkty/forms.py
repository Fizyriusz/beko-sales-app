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
            'target': forms.Select(attrs={'class': 'form-select'}),
            'prog_1': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'prog_1_premia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'prog_2': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'prog_2_premia': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'mnoznik_mix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'prog_mix': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'typ': forms.Select(attrs={'class': 'form-select', 'id': 'id_typ'}),
        }
        labels = {
            'nazwa': 'Nazwa zadania',
            'opis': 'Opis',
            'data_start': 'Data rozpoczęcia',
            'data_koniec': 'Data zakończenia',
            'typ': 'Typ zadania',
            'target': 'Cel liczony wg',
            'prog_1': 'Próg 1 (szt.)',
            'prog_1_premia': 'Premia za próg 1 (PLN)',
            'prog_2': 'Próg 2 (szt.)',
            'prog_2_premia': 'Premia za próg 2 (PLN)',
            'prog_mix': 'Próg mix (szt.)',
            'mnoznik_mix': 'Mnożnik stawki',
        }
        help_texts = {
            'prog_1_premia': 'Kwota wypłacana po osiągnięciu progu 1.',
            'prog_2_premia': 'Kwota wypłacana po osiągnięciu progu 2 (ma pierwszeństwo przed progiem 1).',
            'mnoznik_mix': 'Np. 1.5 = stawka podniesiona o 50% po przekroczeniu progu mix.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Zadania zapisane przed wprowadzeniem typow moga miec pusty typ -
        # podstawiamy sensowna wartosc, zeby edycja nie wysypywala walidacji.
        if not self.initial.get('typ') and not self.data.get('typ'):
            self.initial['typ'] = Zadanie.Typ.KONKRETNE_MODELE

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


from .models import Hala, TargetHali

MIESIACE_PL = [
    (1, 'Styczeń'), (2, 'Luty'), (3, 'Marzec'), (4, 'Kwiecień'),
    (5, 'Maj'), (6, 'Czerwiec'), (7, 'Lipiec'), (8, 'Sierpień'),
    (9, 'Wrzesień'), (10, 'Październik'), (11, 'Listopad'), (12, 'Grudzień'),
]


class HalaForm(forms.ModelForm):
    class Meta:
        model = Hala
        fields = ['nazwa', 'opis', 'pracownicy', 'aktywna']
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Media Expert Rzeszów'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pracownicy': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
            'aktywna': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TargetHaliForm(forms.ModelForm):
    miesiac = forms.TypedChoiceField(
        choices=[('', '— (target kwartalny) —')] + MIESIACE_PL,
        coerce=int, required=False, empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select'}), label="Miesiąc",
    )

    class Meta:
        model = TargetHali
        fields = ['typ', 'rok', 'kwartal', 'miesiac', 'cel_beko', 'cel_whirlpool']
        widgets = {
            'typ': forms.Select(attrs={'class': 'form-select'}),
            'rok': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2100}),
            'kwartal': forms.Select(attrs={'class': 'form-select'}),
            'cel_beko': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'cel_whirlpool': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean(self):
        cleaned = super().clean()
        typ = cleaned.get('typ')
        miesiac = cleaned.get('miesiac')

        if typ == TargetHali.Typ.MIESIECZNY and not miesiac:
            self.add_error('miesiac', "Target miesięczny wymaga wskazania miesiąca.")
        if typ == TargetHali.Typ.KWARTALNY:
            cleaned['miesiac'] = None

        if cleaned.get('cel_beko') in (None, 0) and cleaned.get('cel_whirlpool') in (None, 0):
            self.add_error(None, "Podaj cel dla Beko lub dla Whirlpool (albo dla obu).")
        return cleaned


from .models import Alejka, ObiektMapy

class AlejkaForm(forms.ModelForm):
    class Meta:
        model = Alejka
        fields = [
            'nazwa', 'opis', 'orientacja', 'dlugosc',
            'pozycja_x', 'pozycja_y', 'kolejnosc', 'aktywna',
        ]
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orientacja': forms.Select(attrs={'class': 'form-select'}),
            'dlugosc': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 40}),
            'pozycja_x': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 60}),
            'pozycja_y': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 60}),
            'kolejnosc': forms.NumberInput(attrs={'class': 'form-control'}),
            'aktywna': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_dlugosc(self):
        d = self.cleaned_data.get('dlugosc')
        if d is not None and d < 1:
            raise forms.ValidationError("Długość musi wynosić co najmniej 1.")
        return d


class ObiektMapyForm(forms.ModelForm):
    class Meta:
        model = ObiektMapy
        fields = ['nazwa', 'opis', 'typ', 'pozycja_x', 'pozycja_y', 'szerokosc', 'wysokosc', 'aktywny']
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'np. Stanowisko projektowania mebli'}),
            'opis': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'typ': forms.Select(attrs={'class': 'form-select'}),
            'pozycja_x': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 60}),
            'pozycja_y': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 60}),
            'szerokosc': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 40}),
            'wysokosc': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 40}),
            'aktywny': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
