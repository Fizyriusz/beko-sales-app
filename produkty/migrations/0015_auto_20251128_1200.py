from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produkty', '0014_zadanie_prog_1_premia_zadanie_prog_2_premia_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sprzedaz',
            name='task',
        ),
        migrations.AddField(
            model_name='zadanie',
            name='opis',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='zadanie',
            name='mnoznik_mix',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Mnożnik dla zadań typu mix', max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name='zadanie',
            name='prog_mix',
            field=models.PositiveIntegerField(blank=True, help_text='Próg dla zadań typu mix', null=True),
        ),
        migrations.AddField(
            model_name='zadanie',
            name='typ',
            field=models.CharField(choices=[('MIX_PROWIZJA', 'Mix prowizja'), ('MIX_MNOZNIK', 'Mix mnożnik'), ('KONKRETNE_MODELE', 'Konkretne modele')], default='KONKRETNE_MODELE', max_length=20),
        ),
        migrations.AlterField(
            model_name='zadanie',
            name='produkty',
            field=models.ManyToManyField(blank=True, related_name='zadania', to='produkty.Produkt'),
        ),
        migrations.AddField(
            model_name='sprzedaz',
            name='zadanie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='produkty.zadanie'),
        ),
    ]
