# Generated by Django 5.1.3 on 2025-01-21 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("produkty", "0008_rename_liczba_sztuk_ekspozycja_liczba"),
    ]

    operations = [
        migrations.RenameField(
            model_name="task",
            old_name="data_rozpoczecia",
            new_name="data_do",
        ),
        migrations.RenameField(
            model_name="task",
            old_name="data_zakonczenia",
            new_name="data_od",
        ),
        migrations.AddField(
            model_name="task",
            name="mnoznik_stawki",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="Mnożnik dla stawki produktów",
                max_digits=4,
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="minimalna_liczba_sztuk",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="task",
            name="opis",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="task",
            name="produkty",
            field=models.ManyToManyField(related_name="zadania", to="produkty.produkt"),
        ),
    ]
