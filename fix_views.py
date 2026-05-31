import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if "return render(request, 'produkty/zadanie_form.html', {" in line and "selected_products_pks" in lines[i-3]:
            # This is inside zadanie_edytuj
            # We want to replace from this line up to `def zamkniecie_dnia(request):`
            for j in range(i, len(lines)):
                if "def zamkniecie_dnia(request):" in lines[j]:
                    end_idx = j - 1 # previous line should be @login_required
                    break
            
            # The replacement text
            replacement = """    return render(request, 'produkty/zadanie_form.html', {
        'form': form, 
        'zadanie': zadanie,
        'selected_products_pks': selected_products_pks
    })

@login_required
def zadanie_usun(request, zadanie_id):
    \"\"\"Widok do usuwania zadania\"\"\"
    zadanie = get_object_or_404(Zadanie, id=zadanie_id)
    
    if request.method == 'POST':
        month = zadanie.data_start.month
        year = zadanie.data_start.year
        zadanie.delete()
        return redirect('produkty:zadania_view', year=year, month=month)
    
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

    # Analiza historyczna
    days = request.GET.get('days', '90')
    if days not in ['30', '60', '90']:
        days = '90'
    days_int = int(days)
    
    today = datetime.now().date()
    start_date_hist = today - timedelta(days=days_int)
    
    historyczne_sprzedaze = Sprzedaz.objects.filter(
        produkt__in=modele_w_zadaniu,
        data_sprzedazy__range=(start_date_hist, today)
    ).values('produkt').annotate(ilosc=Sum('liczba_sztuk'))
    
    historia_dict = {item['produkt']: item['ilosc'] for item in historyczne_sprzedaze}
    
    analiza_dane = []
    for prod in modele_w_zadaniu:
        sztuk = historia_dict.get(prod.id, 0)
        analiza_dane.append({
            'produkt': prod,
            'sztuk': sztuk
        })
    analiza_dane.sort(key=lambda x: x['sztuk'], reverse=True)

    context = {
        'zadanie': zadanie,
        'postep': postep,
        'sprzedane_modele': sprzedane_modele,
        'modele_w_zadaniu': modele_w_zadaniu,
        'prog_1_status': prog_1_status,
        'prog_2_status': prog_2_status,
        'analiza_dane': analiza_dane,
        'selected_days': days_int,
    }

    return render(request, 'produkty/szczegoly_zadania.html', context)

@login_required
def otwarcie_dnia(request):
    import datetime
    today = datetime.date.today()
    from django.utils import timezone
    
    dzien, created = DzienPracy.objects.get_or_create(
        user=request.user,
        data=today,
        defaults={'czas_otwarcia': timezone.now()}
    )
    if created:
        messages.success(request, "Pomyślnie rozpoczęto dzień pracy!")
    else:
        messages.info(request, "Dzień pracy został już rozpoczęty wcześniej.")
    return redirect('produkty:home')

@login_required
"""
            new_lines = lines[:i] + [replacement] + lines[end_idx:]
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print("Fixed successfully")
            return

if __name__ == "__main__":
    fix_file(sys.argv[1])
