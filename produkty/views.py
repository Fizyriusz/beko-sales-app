from django.shortcuts import render, redirect, get_object_or_404
from .models import Produkt, Sprzedaz, Zadanie, Ekspozycja, GrupaProduktowa, Marka, KlientCounter
from .forms import ZadanieForm, ProduktForm
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from zipfile import BadZipFile
from decimal import Decimal, InvalidOperation
import logging
from django.utils import timezone
from django.db.models import Sum, Count, F
from collections import defaultdict
from datetime import timedelta, datetime
from rapidfuzz import fuzz, process 
import re
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import calendar

@login_required
def test_template(request):
    try:
        template = get_template('produkty/import_form.html')
        return render(request, 'produkty/import_form.html')  # Jeśli działa, to powinno pokazać poprawny szablon
    except TemplateDoesNotExist:
        return render(request, 'produkty/home.html', {'error': 'Szablon nie istnieje'})

@login_required
def home(request):
    today = datetime.now().date()
    # Tydzień zaczyna się w poniedziałek (weekday() == 0)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_of_month = today.replace(day=1)
    # Znajdź ostatni dzień miesiąca
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    sprzedaz_tygodniowa = Sprzedaz.objects.filter(data_sprzedazy__range=[start_of_week, end_of_week])
    sprzedaz_miesieczna = Sprzedaz.objects.filter(data_sprzedazy__range=[start_of_month, end_of_month])

    # Obliczanie sum prowizji
    tygodniowa_suma = sprzedaz_tygodniowa.aggregate(
        total=Sum(F('liczba_sztuk') * F('produkt__stawka') + F('prowizja'), output_field=models.DecimalField())
    )['total'] or Decimal('0.00')

    miesieczna_suma = sprzedaz_miesieczna.aggregate(
        total=Sum(F('liczba_sztuk') * F('produkt__stawka') + F('prowizja'), output_field=models.DecimalField())
    )['total'] or Decimal('0.00')


    # Pobierz licznik klientów na dziś
    licznik, _ = KlientCounter.objects.get_or_create(data=today)

    najczesciej_sprzedawane = Sprzedaz.objects.filter(
        data_sprzedazy__gte=start_of_month
    ).values('produkt__model').annotate(
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
    if request.method == 'POST' and 'file' in request.FILES:
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
    elif request.method == 'POST':
        # Brak pliku w żądaniu POST
        return render(request, 'produkty/import_form.html', {'error': 'Nie wybrano pliku do importu.'})

    return render(request, 'produkty/import_form.html')

logger = logging.getLogger(__name__)


def _zapisz_sprzedaz_i_zadania(zatwierdzone_modele, data_sprzedazy):
    for model in zatwierdzone_modele:
        produkt, _ = Produkt.objects.get_or_create(
            model=model,
            defaults={'stawka': 0, 'grupa_towarowa': 'NIEZNANA'}
        )
        sprzedaz = Sprzedaz.objects.create(
            produkt=produkt,
            data_sprzedazy=data_sprzedazy,
            liczba_sztuk=1
        )

        wszystkie_zadania = Zadanie.objects.filter(data_start__lte=data_sprzedazy, data_koniec__gte=data_sprzedazy)
        for zadanie in wszystkie_zadania:
            if produkt in zadanie.produkty.all():
                sprzedane = Sprzedaz.objects.filter(
                    produkt__in=zadanie.produkty.all(),
                    data_sprzedazy__range=[zadanie.data_start, zadanie.data_koniec]
                ).aggregate(models.Sum('liczba_sztuk'))['liczba_sztuk__sum'] or 0

                if zadanie.typ == 'MIX_MNOZNIK' and sprzedane >= zadanie.prog_mix:
                    sprzedaz.prowizja = produkt.stawka * zadanie.mnoznik_mix
                    sprzedaz.save()


@login_required
def sprzedaz(request):
    if request.method == 'POST':
        if 'sugestie_zatwierdzone' in request.POST:
            data_sprzedazy = request.POST.get('data_sprzedazy')

            zatwierdzone_modele = []
            for key in request.POST:
                if key.startswith('model_'):
                    model = request.POST[key].strip().upper()
                    zatwierdzone_modele.append(model)

            _zapisz_sprzedaz_i_zadania(zatwierdzone_modele, data_sprzedazy)
            return redirect('produkty:sprzedaz_sukces')

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
                zatwierdzone_modele.append(model)
            else:
                najlepszy_wynik = process.extractOne(model, wszystkie_modele, scorer=fuzz.ratio)
                if najlepszy_wynik and najlepszy_wynik[1] > 80:
                    sugestie.append((model, najlepszy_wynik[0]))
                else:
                    Produkt.objects.get_or_create(
                        model=model,
                        defaults={'stawka': 0, 'grupa_towarowa': 'NIEZNANA'}
                    )
                    zatwierdzone_modele.append(model)

        if sugestie:
            context = {
                'sugestie': sugestie,
                'data_sprzedazy': data_sprzedazy,
                'zatwierdzone_modele': zatwierdzone_modele,
            }
            return render(request, 'produkty/sprzedaz_sugestie.html', context)

        _zapisz_sprzedaz_i_zadania(zatwierdzone_modele, data_sprzedazy)
        return redirect('produkty:sprzedaz_sukces')

    return render(request, 'produkty/sprzedaz.html')

@login_required
def sprzedaz_sukces(request):
    return render(request, 'produkty/sprzedaz_sukces.html')

@login_required
def podsumowanie_sprzedazy(request):
    data_od = request.GET.get('data_od')
    data_do = request.GET.get('data_do')
    produkt_nazwa = request.GET.get('produkt')
    marka_nazwa = request.GET.get('marka')

    if not data_od and not data_do:
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        data_od = start_of_month.strftime('%Y-%m-%d')
        data_do = end_of_month.strftime('%Y-%m-%d')

    # Nawigacja po miesiącach
    current_month_start = datetime.strptime(data_od, '%Y-%m-%d').date()
    
    prev_month_end = current_month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)
    next_month_end = (next_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    sprzedaz_qs = Sprzedaz.objects.select_related('produkt').all()

    if data_od:
        sprzedaz_qs = sprzedaz_qs.filter(data_sprzedazy__gte=data_od)
    if data_do:
        sprzedaz_qs = sprzedaz_qs.filter(data_sprzedazy__lte=data_do)
    if produkt_nazwa:
        sprzedaz_qs = sprzedaz_qs.filter(produkt__model__icontains=produkt_nazwa)
    if marka_nazwa:
        sprzedaz_qs = sprzedaz_qs.filter(produkt__marka__icontains=marka_nazwa)

    # Annotate with the commission for each sale
    sprzedaz_annotated = sprzedaz_qs.annotate(
        obliczona_prowizja=models.F('liczba_sztuk') * models.F('produkt__stawka')
    )

    sprzedaz_podsumowanie = (
        sprzedaz_annotated
        .values('produkt__marka', 'produkt__model', 'produkt__stawka')
        .annotate(
            liczba_sztuk=Sum('liczba_sztuk'),
            suma_prowizji=Sum('obliczona_prowizja')
        )
        .order_by('-suma_prowizji')
    )

    agregaty = sprzedaz_annotated.aggregate(
        calkowita_liczba_sztuk=Sum('liczba_sztuk'),
        calkowita_prowizja=Sum('obliczona_prowizja')
    )

    context = {
        'sprzedaz': sprzedaz_podsumowanie,
        'liczba_sztuk': agregaty['calkowita_liczba_sztuk'] or 0,
        'calkowita_prowizja': agregaty['calkowita_prowizja'] or 0,
        'data_od': data_od,
        'data_do': data_do,
        'produkt': produkt_nazwa,
        'marka': marka_nazwa,
        'prev_month_data_od': prev_month_start.strftime('%Y-%m-%d'),
        'prev_month_data_do': prev_month_end.strftime('%Y-%m-%d'),
        'next_month_data_od': next_month_start.strftime('%Y-%m-%d'),
        'next_month_data_do': next_month_end.strftime('%Y-%m-%d'),
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
def zadania_management(request):
    """Widok do zarządzania zadaniami"""
    today = datetime.now().date()
    return redirect('produkty:zadania_view', year=today.year, month=today.month)

@login_required
def zadania_view(request, year, month):
    """Widok do wyświetlania zadań w ujęciu miesięcznym"""
    zadania = Zadanie.objects.filter(
        data_start__year=year, data_start__month=month
    ).order_by('-data_start')

    first_day_of_month = datetime(year, month, 1)
    prev_month_date = first_day_of_month - timedelta(days=1)
    next_month_date = (first_day_of_month + timedelta(days=32)).replace(day=1)

    context = {
        'zadania': zadania,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'prev_year': prev_month_date.year,
        'prev_month': prev_month_date.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
    }
    return render(request, 'produkty/zadania.html', context)


@login_required
def zadanie_dodaj(request):
    """Widok do dodawania nowego zadania"""
    if request.method == 'POST':
        form = ZadanieForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('produkty:zadania_management')
    else:
        form = ZadanieForm()
    
    return render(request, 'produkty/zadanie_form.html', {
        'form': form,
        'selected_products_pks': []
    })

@login_required
def zadanie_edytuj(request, zadanie_id):
    """Widok do edycji istniejącego zadania"""
    zadanie = get_object_or_404(Zadanie, id=zadanie_id)
    
    if request.method == 'POST':
        form = ZadanieForm(request.POST, instance=zadanie)
        if form.is_valid():
            form.save()
            return redirect('produkty:zadania_management')
    else:
        form = ZadanieForm(instance=zadanie)

    selected_products_pks = list(zadanie.produkty.values_list('pk', flat=True))

    return render(request, 'produkty/zadanie_form.html', {
        'form': form, 
        'zadanie': zadanie,
        'selected_products_pks': selected_products_pks
    })

@login_required
def zadanie_usun(request, zadanie_id):
    """Widok do usuwania zadania"""
    zadanie = get_object_or_404(Zadanie, id=zadanie_id)
    
    if request.method == 'POST':
        zadanie.delete()
        return redirect('produkty:zadania_management')
    
    return render(request, 'produkty/zadanie_usun.html', {'zadanie': zadanie})

@login_required
def szczegoly_zadania(request, zadanie_id):
    zadanie = get_object_or_404(Zadanie, id=zadanie_id)
    modele_w_zadaniu = zadanie.produkty.all()

    sprzedaz_w_okresie = Sprzedaz.objects.filter(
        produkt__in=modele_w_zadaniu,
        data_sprzedazy__range=(zadanie.data_start, zadanie.data_koniec)
    )

    postep = sprzedaz_w_okresie.aggregate(suma=Sum('liczba_sztuk'))['suma'] or 0
    prog_1_status = False
    if zadanie.prog_1 and postep >= zadanie.prog_1:
        prog_1_status = True

    prog_2_status = False
    if zadanie.prog_2 and postep >= zadanie.prog_2:
        prog_2_status = True

    sprzedane_modele = sprzedaz_w_okresie.values('produkt__model', 'produkt__marka').annotate(
        ilosc=Sum('liczba_sztuk')
    ).order_by('-ilosc')

    context = {
        'zadanie': zadanie,
        'postep': postep,
        'sprzedane_modele': sprzedane_modele,
        'modele_w_zadaniu': modele_w_zadaniu,
        'prog_1_status': prog_1_status,
        'prog_2_status': prog_2_status,
    }

    return render(request, 'produkty/szczegoly_zadania.html', context)

@login_required
def calendar_view(request, year=None, month=None):
    today = datetime.now().date()
    if year is None or month is None:
        year = today.year
        month = today.month

    # Pobieranie sprzedaży dla danego miesiąca i obliczanie prowizji
    sales_in_month = Sprzedaz.objects.filter(
        data_sprzedazy__year=year,
        data_sprzedazy__month=month
    ).annotate(
        commission=models.F('liczba_sztuk') * models.F('produkt__stawka') + models.F('prowizja')
    ).values('data_sprzedazy').annotate(
        total_items=Sum('liczba_sztuk'),
        total_commission=Sum('commission')
    ).order_by('data_sprzedazy')

    sales_by_day = {
        sale['data_sprzedazy'].day: {
            'total_items': sale['total_items'],
            'total_commission': sale['total_commission']
        } for sale in sales_in_month
    }

    # Ustawienia kalendarza
    cal = calendar.Calendar()
    month_days = cal.monthdayscalendar(year, month)

    # Poprzedni i następny miesiąc
    first_day_of_month = datetime(year, month, 1)
    prev_month_date = first_day_of_month - timedelta(days=1)
    next_month_date = (first_day_of_month + timedelta(days=32)).replace(day=1)

    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'month_days': month_days,
        'sales_by_day': sales_by_day,
        'today': today,
        'prev_year': prev_month_date.year,
        'prev_month': prev_month_date.month,
        'next_year': next_month_date.year,
        'next_month': next_month_date.month,
    }
    return render(request, 'produkty/calendar.html', context)



@login_required

def daily_sales_view(request, year, month, day):
    date_of_sales = datetime(year, month, day).date()
    sales = Sprzedaz.objects.filter(data_sprzedazy=date_of_sales).select_related('produkt').annotate(
        total_commission=models.F('liczba_sztuk') * models.F('produkt__stawka') + models.F('prowizja')
    )

    totals = sales.aggregate(
        total_items_sum=Sum('liczba_sztuk'),
        total_commission_sum=Sum('total_commission')
    )

    context = {
        'date_of_sales': date_of_sales,
        'sales': sales,
        'total_items': totals['total_items_sum'],
        'total_commission': totals['total_commission_sum'],
    }
    return render(request, 'produkty/daily_sales.html', context)



@staff_member_required

def delete_sales_for_day(request):

    message = ''

    if request.method == 'POST':

        date_str = request.POST.get('date')

        if date_str:

            try:

                date_to_delete = datetime.strptime(date_str, '%Y-%m-%d').date()

                sales_to_delete = Sprzedaz.objects.filter(data_sprzedazy=date_to_delete)

                count = sales_to_delete.count()

                sales_to_delete.delete()

                message = f'Pomyślnie usunięto {count} rekordów sprzedaży z dnia {date_to_delete}.'

            except ValueError:

                message = 'Nieprawidłowy format daty. Użyj formatu YYYY-MM-DD.'

        else:

            message = 'Proszę wybrać datę.'



    return render(request, 'produkty/delete_sales_for_day.html', {'message': message})

@login_required
def lista_produktow(request):
    produkty = Produkt.objects.all()

    # Filtering
    model_filter = request.GET.get('model', '')
    marka_filter = request.GET.get('marka', '')
    grupa_towarowa_filter = request.GET.get('grupa_towarowa', '')
    prowizja_od = request.GET.get('prowizja_od', '')
    prowizja_do = request.GET.get('prowizja_do', '')

    if model_filter:
        produkty = produkty.filter(model__icontains=model_filter)
    if marka_filter:
        produkty = produkty.filter(marka__icontains=marka_filter)
    if grupa_towarowa_filter:
        produkty = produkty.filter(grupa_towarowa__icontains=grupa_towarowa_filter)
    if prowizja_od:
        try:
            produkty = produkty.filter(stawka__gte=Decimal(prowizja_od))
        except (InvalidOperation, ValueError):
            pass  # Ignore invalid decimal values
    if prowizja_do:
        try:
            produkty = produkty.filter(stawka__lte=Decimal(prowizja_do))
        except (InvalidOperation, ValueError):
            pass  # Ignore invalid decimal values

    # Grouping
    group_by = request.GET.get('group', None)
    grouped_produkty = None

    if group_by in ['marka', 'grupa_towarowa']:
        grouped_produkty = defaultdict(list)
        for produkt in produkty.order_by(group_by):
            grouped_produkty[getattr(produkt, group_by)].append(produkt)
        # Sort the groups by key, handling None values
        grouped_produkty = dict(sorted(grouped_produkty.items(), key=lambda item: (item[0] is None, item[0])))

    # Sorting
    sort_by = request.GET.get('sort', 'model')
    if sort_by not in ['model', 'marka', 'stawka', 'grupa_towarowa']:
        sort_by = 'model'
    
    direction = request.GET.get('dir', 'asc')
    if direction == 'desc':
        sort_by = f'-{sort_by}'
    
    if not grouped_produkty:
        produkty = produkty.order_by(sort_by)

    context = {
        'produkty': produkty,
        'grouped_produkty': grouped_produkty,
        'group_by': group_by,
        'model_filter': model_filter,
        'marka_filter': marka_filter,
        'grupa_towarowa_filter': grupa_towarowa_filter,
        'prowizja_od': prowizja_od,
        'prowizja_do': prowizja_do,
        'sort': request.GET.get('sort', 'model'),
        'dir': request.GET.get('dir', 'asc'),
    }
    return render(request, 'produkty/lista_produktow.html', context)

@login_required
def product_edit(request, product_id):
    produkt = get_object_or_404(Produkt, pk=product_id)
    if request.method == 'POST':
        form = ProduktForm(request.POST, instance=produkt)
        if form.is_valid():
            form.save()
            return redirect('produkty:lista_produktow')
    else:
        form = ProduktForm(instance=produkt)
    return render(request, 'produkty/product_edit.html', {'form': form})

