# Generated by Django 5.1.3 on 2024-11-18 23:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("produkty", "0003_sprzedaz"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sprzedaz",
            old_name="ilosc_sztuk",
            new_name="liczba_sztuk",
        ),
        migrations.RemoveField(
            model_name="sprzedaz",
            name="model",
        ),
        migrations.AddField(
            model_name="sprzedaz",
            name="produkt",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="produkty.produkt",
            ),
            preserve_default=False,
        ),
    ]
