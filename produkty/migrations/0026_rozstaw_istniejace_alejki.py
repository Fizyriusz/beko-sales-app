from django.db import migrations


def rozstaw_alejki(apps, schema_editor):
    """Istniejace alejki nie mialy wspolrzednych - rozstawiamy je w rzedzie
    wedlug dotychczasowej kolejnosci, zeby mapa wygladala jak przed zmiana."""
    Alejka = apps.get_model('produkty', 'Alejka')
    for idx, a in enumerate(Alejka.objects.all().order_by('kolejnosc', 'nazwa')):
        a.pozycja_x = idx * 3
        a.pozycja_y = 1
        a.orientacja = 'V'
        a.dlugosc = 8
        a.save(update_fields=['pozycja_x', 'pozycja_y', 'orientacja', 'dlugosc'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('produkty', '0025_obiektmapy_alejka_dlugosc_alejka_orientacja_and_more'),
    ]

    operations = [
        migrations.RunPython(rozstaw_alejki, noop),
    ]
