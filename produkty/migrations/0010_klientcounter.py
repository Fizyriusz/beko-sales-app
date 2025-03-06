# Generated by Django 5.1.3 on 2025-03-06 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produkty', '0009_rename_data_rozpoczecia_task_data_do_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='KlientCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(auto_now_add=True)),
                ('liczba_klientow', models.IntegerField(default=0)),
                ('notatka', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
