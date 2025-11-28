from django.db import migrations

def migrate_task_to_zadanie(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('produkty', '0015_auto_20251128_1200'),
    ]

    operations = [
        migrations.RunPython(migrate_task_to_zadanie),
    ]
