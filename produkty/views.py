from django.shortcuts import render, redirect, get_object_or_404
from .models import Produkt, Sprzedaz, Task, Ekspozycja, GrupaProduktowa, Marka, KlientCounter
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from zipfile import BadZipFile
from decimal import Decimal, InvalidOperation
import logging
from django.utils import timezone
from django.db.models import Sum
from collections import defaultdict
from datetime import timedelta
from rapidfuzz import fuzz, process 
import re
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO

@login_required
def test_template(request):
    try:
        template = get_template('produkty/import_form.html')
        return render(request, 'produkty/import_form.html')  # Jeśli działa, to powinno pokazać poprawny szablon
    except TemplateDoesNotExist:
        return render(request, 'produkty/home.html', {'error': 'Szablon nie istnieje'})

@login_required
def home(request):
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    sprzedaz_tygodniowa = Sprzedaz.objects.filter(data_sprzedazy__gte=start_of_week)
    sprzedaz_miesieczna = Sprzedaz.objects.filter(data_sprzedazy__gte=start_of_month)

    # Obliczanie sum prowizji
    tygodniowa_suma = sum(
        sprzedaz.produkt.stawka * sprzedaz.liczba_sztuk 
        for sprzedaz in sprzedaz_tygodniowa
    )
    miesieczna_suma = sum(
        sprzedaz.produkt.stawka * sprzedaz.liczba_sztuk 
        for sprzedaz in sprzedaz_miesieczna
    )

    # Pobierz licznik klientów na dziś
    licznik, _ = KlientCounter.objects.get_or_create(data=today)

    najczesciej_sprzedawane = Sprzedaz.objects.values('produkt__model').annotate(
        liczba_sztuk=Sum('liczba_sztuk')
    ).order_by('-liczba_sztuk')[:5]

    context = {
        'najczesciej_sprzedawane': najczesciej_sprzedawane,
        'tygodniowa_suma': tygodniowa_suma,
        'miesieczna_suma': miesieczna_suma,
        'licznik_klientow': licznik.liczba_klientow,
    }

    return render(request, 'produkty/home.html', context)
# Ustaw logger
logger = logging.getLogger(__name__)

@login_required
def import_excel(request):
    if request.method == 'POST' and request.FILES['file']:
        excel_file = request.FILES['file']
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
        except (InvalidFileException, BadZipFile) as e:
            logger.error(f"Nieprawidłowy plik Excel: {e}")
            return render(request, 'produkty/import_form.html', {
                'error': 'Nieprawidłowy plik Excel. Upewnij się, że przesyłasz prawidłowy plik.'
            })
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas wczytywania pliku: {e}")
            return render(request, 'produkty/import_form.html', {
                'error': 'Wystąpił błąd podczas przetwarzania pliku.'
            })

        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            # Nowy format: A-grupa_towarowa, B-marka (BRAND), C-model, D-stawka
            if len(row) < 4:
                logger.warning(f"Wiersz {idx} pominięty - niewystarczająca liczba kolumn.")
                continue

            grupa_towarowa, marka, model, stawka = row[0], row[1], row[2], row[3]

            # Pomijamy wiersze, w których brakuje kluczowych danych
            if not model:
                logger.warning(f"Wiersz {idx} pominięty - brak modelu.")
                continue

            try:
                # Obsługa stawki
                if stawka is None or stawka == '':
                    stawka = Decimal(0)
                else:
                    stawka = Decimal(stawka)
            except (TypeError, InvalidOperation) as e:
                logger.error(f"Błąd konwersji stawki w wierszu {idx}: {stawka}. Ustawiono 0. Błąd: {e}")
                stawka = Decimal(0)  # Domyślna wartość

            # Dodawanie produktu z marką
            try:
                Produkt.objects.update_or_create(
                    model=model,
                    defaults={
                        'stawka': stawka,
                        'grupa_towarowa': grupa_towarowa or 'Nieznana',
                        'marka': marka or 'Nieznana'
                    }
                )
            except Exception as e:
                logger.error(f"Błąd podczas tworzenia produktu w wierszu {idx}: {e}")
        
        return render(request, 'produkty/import_success.html')

    return render(request, 'produkty/import_form.html')

logger = logging.getLogger(__name__)

@login_required
def sprzedaz(request):
    if request.method == 'POST':
        # Obsługa zatwierdzenia sugestii
        if 'sugestie_zatwierdzone' in request.POST:
            data_sprzedazy = request.POST.get('data_sprzedazy')

            # Przetwarzanie modeli, które użytkownik zatwierdził
            modele = []
            for key in request.POST:
                if key.startswith('model_'):
                    model = request.POST[key].strip().upper()
                    modele.append(model)

            for model in modele:
                produkt, created = Produkt.objects.get_or_create(
                    model=model,
                    defaults={'stawka': 0, 'grupa_towarowa': 'NIEZNANA'}
                )
                sprzedaz = Sprzedaz.objects.create(
                    produkt=produkt,
                    data_sprzedazy=data_sprzedazy,
                    liczba_sztuk=1
                )

                # Sprawdź, czy produkt pasuje do jakiegoś zadania
                wszystkie_zadania = Task.objects.filter(data_od__lte=data_sprzedazy, data_do__gte=data_sprzedazy)
                for zadanie in wszystkie_zadania:
                    if produkt in zadanie.produkty.all():
                        # Oblicz liczbę sprzedanych produktów dla zadania
                        sprzedane = Sprzedaz.objects.filter(
                            produkt__in=zadanie.produkty.all(),
                            data_sprzedazy__range=[zadanie.data_od, zadanie.data_do]
                        ).aggregate(models.Sum('liczba_sztuk'))['liczba_sztuk__sum'] or 0

                        # Jeśli spełniono warunek minimalnej liczby sztuk, zastosuj mnożnik stawki
                        if sprzedane >= zadanie.minimalna_liczba_sztuk:
                            sprzedaz.prowizja = produkt.stawka * zadanie.mnoznik_stawki
                            sprzedaz.save()

            return redirect('produkty:sprzedaz_sukces')

        # Obsługa wprowadzenia nowych modeli sprzedaży
        data_sprzedazy = request.POST.get('data_sprzedazy')
        modele_sprzedazy = request.POST.get('modele_sprzedazy')

        if modele_sprzedazy:
            modele = [model.strip().upper() for model in modele_sprzedazy.split('\n') if model.strip()]
        else:
            modele = []

        wszystkie_modele = Produkt.objects.values_list('model', flat=True)

        sugestie = []
        zatwierdzone_modele = []

        for model in modele:
            if model in wszystkie_modele:
                # Jeśli model istnieje w bazie, zapisz sprzedaż
                produkt = Produkt.objects.get(model=model)
                sprzedaz = Sprzedaz.objects.create(
                    produkt=produkt,
                    data_sprzedazy=data_sprzedazy,
                    liczba_sztuk=1
                )
                zatwierdzone_modele.append(model)

                # Sprawdź, czy produkt pasuje do jakiegoś zadania
                wszystkie_zadania = Task.objects.filter(data_od__lte=data_sprzedazy, data_do__gte=data_sprzedazy)
                for zadanie in wszystkie_zadania:
                    if produkt in zadanie.produkty.all():
                        # Oblicz liczbę sprzedanych produktów dla zadania
                        sprzedane = Sprzedaz.objects.filter(
                            produkt__in=zadanie.produkty.all(),
                            data_sprzedazy__range=[zadanie.data_od, zadanie.data_do]
                        ).aggregate(models.Sum('liczba_sztuk'))['liczba_sztuk__sum'] or 0

                        # Jeśli spełniono warunek minimalnej liczby sztuk, zastosuj mnożnik stawki
                        if sprzedane >= zadanie.minimalna_liczba_sztuk:
                            sprzedaz.prowizja = produkt.stawka * zadanie.mnoznik_stawki
                            sprzedaz.save()
            else:
                # Jeśli model nie istnieje, znajdź najbardziej podobny model
                najlepszy_wynik = process.extractOne(model, wszystkie_modele, scorer=fuzz.ratio)
                if najlepszy_wynik and najlepszy_wynik[1] > 80:  # Próg podobieństwa, który można dostosować
                    sugestie.append((model, najlepszy_wynik[0]))
                else:
                    # Jeśli nie znaleziono dobrego dopasowania, dodaj nowy produkt z domyślną stawką 0
                    produkt, created = Produkt.objects.get_or_create(
                        model=model,
                        defaults={'stawka': 0, 'grupa_towarowa': 'NIEZNANA'}
                    )
                    sprzedaz = Sprzedaz.objects.create(
                        produkt=produkt,
                        data_sprzedazy=data_sprzedazy,
                        liczba_sztuk=1
                    )
                    zatwierdzone_modele.append(model)

                    # Sprawdź, czy produkt pasuje do jakiegoś zadania
                    wszystkie_zadania = Task.objects.filter(data_od__lte=data_sprzedazy, data_do__gte=data_sprzedazy)
                    for zadanie in wszystkie_zadania:
                        if produkt in zadanie.produkty.all():
                            # Oblicz liczbę sprzedanych produktów dla zadania
                            sprzedane = Sprzedaz.objects.filter(
                                produkt__in=zadanie.produkty.all(),
                                data_sprzedazy__range=[zadanie.data_od, zadanie.data_do]
                            ).aggregate(models.Sum('liczba_sztuk'))['liczba_sztuk__sum'] or 0

                            # Jeśli spełniono warunek minimalnej liczby sztuk, zastosuj mnożnik stawki
                            if sprzedane >= zadanie.minimalna_liczba_sztuk:
                                sprzedaz.prowizja = produkt.stawka * zadanie.mnoznik_stawki
                                sprzedaz.save()

        # Jeśli są sugestie, wyświetl je w formularzu
        if sugestie:
            context = {
                'sugestie': sugestie,
                'data_sprzedazy': data_sprzedazy,
                'zatwierdzone_modele': zatwierdzone_modele,
            }
            return render(request, 'produkty/sprzedaz_sugestie.html', context)

        return redirect('produkty:sprzedaz_sukces')

    return render(request, 'produkty/sprzedaz.html')

@login_required
def sprzedaz_sukces(request):
    return render(request, 'produkty/sprzedaz_sukces.html')

@login_required
def podsumowanie_sprzedazy(request):
    # Pobieranie wartości filtrów z GET
    data_od = request.GET.get('data_od')
    data_do = request.GET.get('data_do')
    produkt = request.GET.get('produkt')
    marka = request.GET.get('marka')

    # Tworzenie podstawowego zapytania do modelu Sprzedaz
    sprzedaz = Sprzedaz.objects.all()

    # Filtracja na podstawie daty
    if data_od:
        sprzedaz = sprzedaz.filter(data_sprzedazy__gte=data_od)
    if data_do:
        sprzedaz = sprzedaz.filter(data_sprzedazy__lte=data_do)

    # Filtracja na podstawie produktu i marki
    if produkt:
        sprzedaz = sprzedaz.filter(produkt__model__icontains=produkt)
    if marka:
        sprzedaz = sprzedaz.filter(produkt__marka__icontains=marka)

    # Grupowanie danych
    sprzedaz_podsumowanie = {}

    # Pobieranie aktywnych zadań
    today = timezone.now().date()
    aktywne_zadania = Task.objects.filter(data_od__lte=today, data_do__gte=today)

    for item in sprzedaz:
        model = item.produkt.model
        marka = item.produkt.marka
        stawka = item.produkt.stawka

        # Sprawdź, czy produkt pasuje do aktywnego zadania i uwzględnij mnożnik stawki
        mnoznik = 1
        for zadanie in aktywne_zadania:
            if item.produkt in zadanie.produkty.all():
                mnoznik = zadanie.mnoznik_stawki
                break

        # Zastosuj mnożnik do stawki
        rzeczywista_stawka = stawka * mnoznik

        klucz = f"{marka}_{model}"  # Używamy string jako klucz zamiast krotki
        
        if klucz not in sprzedaz_podsumowanie:
            sprzedaz_podsumowanie[klucz] = {
                'marka': marka,
                'model': model,
                'liczba_sztuk': 0,
                'stawka': rzeczywista_stawka,
                'suma_prowizji': 0
            }
        
        sprzedaz_podsumowanie[klucz]['liczba_sztuk'] += item.liczba_sztuk
        sprzedaz_podsumowanie[klucz]['suma_prowizji'] += rzeczywista_stawka * item.liczba_sztuk

    # Obliczanie sumarycznych wartości dla wszystkich sprzedaży
    liczba_sztuk = sum(item['liczba_sztuk'] for item in sprzedaz_podsumowanie.values())
    calkowita_prowizja = sum(item['suma_prowizji'] for item in sprzedaz_podsumowanie.values())

    context = {
        'sprzedaz': sprzedaz_podsumowanie,
        'liczba_sztuk': liczba_sztuk,
        'calkowita_prowizja': calkowita_prowizja,
    }

    return render(request, 'produkty/podsumowanie_sprzedazy.html', context)

@login_required
def wyciagnij_liste_modeli(request):
    if request.method == 'POST':
        tekst = request.POST.get('tekst_sprzedazy', '')
        # Wyciągnięcie sekcji MOJE
        wzorzec_moje = re.compile(r'MOJE\s*(.*?)\s*(INNE|$)', re.S)
        wynik_moje = wzorzec_moje.search(tekst)
        if wynik_moje:
            lista_modeli = wynik_moje.group(1).split('\n')
            # Filtrowanie tylko rzeczywistych modeli (np. brak spacji, tylko duże litery i cyfry)
            lista_modeli = [
                model.strip() for model in lista_modeli
                if re.match(r'^[A-Z0-9]+$', model.strip())
            ]
        else:
            lista_modeli = []

        context = {'lista_modeli': lista_modeli}
        return render(request, 'produkty/wyciagnij_liste_modeli.html', context)
    else:
        return render(request, 'produkty/wyciagnij_liste_modeli.html')

@login_required
def lista_zadaniowek(request):
    zadaniowki = Task.objects.all()
    return render(request, 'produkty/lista_zadaniowek.html', {'zadaniowki': zadaniowki})

@login_required
def szczegoly_zadaniowki(request, task_id):
    zadaniowka = get_object_or_404(Task, pk=task_id)
    return render(request, 'produkty/szczegoly_zadaniowki.html', {'zadaniowka': zadaniowka})

@login_required
def postepy_zadaniowki(request, task_id):
    zadaniowka = get_object_or_404(Task, id=task_id)
    produkty = zadaniowka.produkty.all()
    total_sprzedane_sztuki = Sprzedaz.objects.filter(produkt__in=produkty).aggregate(models.Sum('liczba_sztuk'))['liczba_sztuk__sum'] or 0
    pozostaly_cel = max(0, zadaniowka.minimalna_liczba_sztuk - total_sprzedane_sztuki)

    context = {
        'zadaniowka': zadaniowka,
        'produkty': produkty,
        'total_sprzedane_sztuki': total_sprzedane_sztuki,
        'pozostaly_cel': pozostaly_cel,
    }
    return render(request, 'produkty/postepy_zadaniowki.html', context)

@login_required
def ekspozycja_form(request, grupa_id):
    grupa = get_object_or_404(GrupaProduktowa, id=grupa_id)
    marki = Marka.objects.all()

    # Pobierz wszystkie grupy w kolejności po ID
    wszystkie_grupy = list(GrupaProduktowa.objects.order_by('id'))
    obecny_index = wszystkie_grupy.index(grupa)

    # Określ poprzednią i następną grupę
    poprzednia_grupa = wszystkie_grupy[obecny_index - 1] if obecny_index > 0 else None
    nastepna_grupa = wszystkie_grupy[obecny_index + 1] if obecny_index < len(wszystkie_grupy) - 1 else None

    if request.method == 'POST':
        # Usuń istniejące rekordy dla tej grupy, aby uniknąć duplikatów
        Ekspozycja.objects.filter(grupa=grupa).delete()

        for marka in marki:
            liczba = int(request.POST.get(f'marka_{marka.id}', 0))
            Ekspozycja.objects.create(
                grupa=grupa,
                marka=marka,
                liczba=liczba
            )
        
        # Przejdź do następnej grupy lub wyświetl podsumowanie
        if nastepna_grupa:
            return redirect('produkty:ekspozycja_form', grupa_id=nastepna_grupa.id)
        return redirect('produkty:ekspozycja_summary')

    return render(request, 'produkty/ekspozycja_form.html', {
        'grupa': grupa,
        'marki': marki,
        'poprzednia_grupa': poprzednia_grupa,
    })

        
@login_required
def ekspozycja_summary(request):
    # Pobierz wszystkie dane ekspozycji z bazy danych
    ekspozycje = Ekspozycja.objects.select_related('grupa', 'marka').all()

    # Przygotuj dane do wyświetlenia w podsumowaniu
    grupy = GrupaProduktowa.objects.all()

    dane_podsumowania = []
    for grupa in grupy:
        marki_ekspozycji = ekspozycje.filter(grupa=grupa)
        dane_podsumowania.append({
            'grupa': grupa.nazwa,
            'marki': marki_ekspozycji,
        })

    return render(request, 'produkty/ekspozycja_summary.html', {
        'dane_podsumowania': dane_podsumowania,
    })

@login_required
def reset_sprzedaz(request):
    if request.method == 'POST':
        Sprzedaz.objects.all().delete()
        return redirect('produkty:podsumowanie_sprzedazy')
    return redirect('produkty:podsumowanie_sprzedazy')

@login_required
def klienci(request):
    today = timezone.now().date()
    counter, created = KlientCounter.objects.get_or_create(data=today)
    
    context = {
        'counter': counter,
    }
    return render(request, 'produkty/klienci.html', context)

@login_required
def zmien_licznik(request, operacja):
    if request.method == 'POST':
        today = timezone.now().date()
        counter, created = KlientCounter.objects.get_or_create(data=today)
        
        if operacja == 'plus':
            counter.liczba_klientow += 1
        elif operacja == 'minus' and counter.liczba_klientow > 0:
            counter.liczba_klientow -= 1
            
        counter.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'liczba_klientow': counter.liczba_klientow})
        
    return redirect('produkty:klienci')

@login_required
def eksportuj_ekspozycje_xlsx(request):
    # Tworzenie nowego arkusza Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ekspozycja"
    
    # Pobieranie danych
    grupy = GrupaProduktowa.objects.all().order_by('id')
    marki = Marka.objects.all().order_by('id')
    ekspozycje = Ekspozycja.objects.select_related('grupa', 'marka').all()
    
    # Stylizacja
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    header_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    # Nagłówki
    ws['A1'] = "Lista TOTAL duża AGD udziały producentów"
    ws['A1'].font = Font(bold=True)
    ws.merge_cells('A1:BV1')
    
    ws['A2'] = "Kategoria"
    ws['A2'].fill = header_fill
    ws['A2'].font = header_font
    ws['A2'].alignment = header_alignment
    ws['A2'].border = thin_border
    
    ws['B2'] = "Produkty TOTAL suma"
    ws['B2'].fill = header_fill
    ws['B2'].font = header_font
    ws['B2'].alignment = header_alignment
    ws['B2'].border = thin_border
    
    # Dodawanie nagłówków marek
    col_index = 3
    for marka in marki:
        col_letter = get_column_letter(col_index)
        ws[f'{col_letter}2'] = f"{marka.nazwa} ilość"
        ws[f'{col_letter}2'].fill = header_fill
        ws[f'{col_letter}2'].font = header_font
        ws[f'{col_letter}2'].alignment = header_alignment
        ws[f'{col_letter}2'].border = thin_border
        
        col_letter = get_column_letter(col_index + 1)
        ws[f'{col_letter}2'] = f"{marka.nazwa} %"
        ws[f'{col_letter}2'].fill = header_fill
        ws[f'{col_letter}2'].font = header_font
        ws[f'{col_letter}2'].alignment = header_alignment
        ws[f'{col_letter}2'].border = thin_border
        
        col_index += 2
    
    # Wypełnianie danymi
    row_index = 3
    for grupa in grupy:
        # Nazwa grupy
        ws[f'A{row_index}'] = grupa.nazwa
        ws[f'A{row_index}'].border = thin_border
        
        # Obliczanie sumy dla grupy
        suma_grupa = sum([ekspozycja.liczba for ekspozycja in ekspozycje.filter(grupa=grupa)])
        ws[f'B{row_index}'] = suma_grupa
        ws[f'B{row_index}'].border = thin_border
        
        # Wypełnianie danymi dla każdej marki
        col_index = 3
        for marka in marki:
            try:
                ekspozycja = ekspozycje.get(grupa=grupa, marka=marka)
                liczba = ekspozycja.liczba
            except Ekspozycja.DoesNotExist:
                liczba = 0
            
            # Ilość
            col_letter = get_column_letter(col_index)
            ws[f'{col_letter}{row_index}'] = liczba
            ws[f'{col_letter}{row_index}'].border = thin_border
            
            # Procent
            col_letter = get_column_letter(col_index + 1)
            if suma_grupa > 0:
                procent = (liczba / suma_grupa) * 100
                ws[f'{col_letter}{row_index}'] = f"{procent:.1f}%"
            else:
                ws[f'{col_letter}{row_index}'] = "#DIV/0!"
            ws[f'{col_letter}{row_index}'].border = thin_border
            
            col_index += 2
        
        row_index += 1
    
    # Dodawanie wiersza podsumowania
    ws[f'A{row_index}'] = "Udziały producenta w ekspozycji produktów TOTAL"
    ws[f'A{row_index}'].border = thin_border
    
    # Obliczanie sumy całkowitej
    suma_total = sum([ekspozycja.liczba for ekspozycja in ekspozycje])
    ws[f'B{row_index}'] = suma_total
    ws[f'B{row_index}'].border = thin_border
    
    # Wypełnianie podsumowania dla każdej marki
    col_index = 3
    for marka in marki:
        suma_marka = sum([ekspozycja.liczba for ekspozycja in ekspozycje.filter(marka=marka)])
        
        # Ilość
        col_letter = get_column_letter(col_index)
        ws[f'{col_letter}{row_index}'] = suma_marka
        ws[f'{col_letter}{row_index}'].border = thin_border
        
        # Procent
        col_letter = get_column_letter(col_index + 1)
        if suma_total > 0:
            procent = (suma_marka / suma_total) * 100
            ws[f'{col_letter}{row_index}'] = f"{procent:.1f}%"
        else:
            ws[f'{col_letter}{row_index}'] = "#DIV/0!"
        ws[f'{col_letter}{row_index}'].border = thin_border
        
        col_index += 2
    
    # Dostosowanie szerokości kolumn
    for col in range(1, col_index):
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # Zapisywanie do bufora i zwracanie jako odpowiedź HTTP
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=ekspozycja.xlsx'
    
    return response

@login_required
def delete_all_models(request):
    if request.method == 'POST':
        # Usuwanie wszystkich produktów
        Produkt.objects.all().delete()
        return render(request, 'produkty/import_success.html', {'message': 'Wszystkie modele zostały usunięte.'})
    
    # Jeśli nie jest to POST, przekieruj na stronę importu
    return redirect('produkty:import_excel')

@login_required
def zadaniowki_management(request):
    """Widok do zarządzania zadaniówkami"""
    zadaniowki = Task.objects.all().order_by('-data_od')
    return render(request, 'produkty/zadaniowki_management.html', {'zadaniowki': zadaniowki})

@login_required
def zadaniowka_dodaj(request):
    """Widok do dodawania nowej zadaniówki"""
    if request.method == 'POST':
        nazwa = request.POST.get('nazwa')
        opis = request.POST.get('opis', '')
        minimalna_liczba_sztuk = int(request.POST.get('minimalna_liczba_sztuk', 0))
        premia_za_minimalna_liczbe = Decimal(request.POST.get('premia_za_minimalna_liczbe', 0))
        premia_za_dodatkowa_liczbe = Decimal(request.POST.get('premia_za_dodatkowa_liczbe', 0))
        mnoznik_stawki = Decimal(request.POST.get('mnoznik_stawki', 1.0))
        data_od = request.POST.get('data_od')
        data_do = request.POST.get('data_do')
        
        # Tworzenie nowej zadaniówki
        zadaniowka = Task.objects.create(
            nazwa=nazwa,
            opis=opis,
            minimalna_liczba_sztuk=minimalna_liczba_sztuk,
            premia_za_minimalna_liczbe=premia_za_minimalna_liczbe,
            premia_za_dodatkowa_liczbe=premia_za_dodatkowa_liczbe,
            mnoznik_stawki=mnoznik_stawki,
            data_od=data_od,
            data_do=data_do
        )
        
        # Obsługa wybranych produktów
        wybrane_produkty = request.POST.getlist('produkty')
        for produkt_id in wybrane_produkty:
            produkt = get_object_or_404(Produkt, id=produkt_id)
            zadaniowka.produkty.add(produkt)
        
        return redirect('produkty:zadaniowki_management')
    
    # Jeśli metoda GET, wyświetl formularz
    produkty = Produkt.objects.all().order_by('marka', 'model')
    return render(request, 'produkty/zadaniowka_form.html', {'produkty': produkty})

@login_required
def zadaniowka_edytuj(request, zadaniowka_id):
    """Widok do edycji istniejącej zadaniówki"""
    zadaniowka = get_object_or_404(Task, id=zadaniowka_id)
    
    if request.method == 'POST':
        zadaniowka.nazwa = request.POST.get('nazwa')
        zadaniowka.opis = request.POST.get('opis', '')
        zadaniowka.minimalna_liczba_sztuk = int(request.POST.get('minimalna_liczba_sztuk', 0))
        zadaniowka.premia_za_minimalna_liczbe = Decimal(request.POST.get('premia_za_minimalna_liczbe', 0))
        zadaniowka.premia_za_dodatkowa_liczbe = Decimal(request.POST.get('premia_za_dodatkowa_liczbe', 0))
        zadaniowka.mnoznik_stawki = Decimal(request.POST.get('mnoznik_stawki', 1.0))
        zadaniowka.data_od = request.POST.get('data_od')
        zadaniowka.data_do = request.POST.get('data_do')
        
        # Aktualizacja produktów
        zadaniowka.produkty.clear()
        wybrane_produkty = request.POST.getlist('produkty')
        for produkt_id in wybrane_produkty:
            produkt = get_object_or_404(Produkt, id=produkt_id)
            zadaniowka.produkty.add(produkt)
        
        zadaniowka.save()
        return redirect('produkty:zadaniowki_management')
    
    # Jeśli metoda GET, wyświetl formularz z danymi
    produkty = Produkt.objects.all().order_by('marka', 'model')
    wybrane_produkty = zadaniowka.produkty.all().values_list('id', flat=True)
    
    context = {
        'zadaniowka': zadaniowka,
        'produkty': produkty,
        'wybrane_produkty': list(wybrane_produkty)
    }
    
    return render(request, 'produkty/zadaniowka_form.html', context)

@login_required
def zadaniowka_usun(request, zadaniowka_id):
    """Widok do usuwania zadaniówki"""
    zadaniowka = get_object_or_404(Task, id=zadaniowka_id)
    
    if request.method == 'POST':
        zadaniowka.delete()
        return redirect('produkty:zadaniowki_management')
    
    return render(request, 'produkty/zadaniowka_usun.html', {'zadaniowka': zadaniowka})