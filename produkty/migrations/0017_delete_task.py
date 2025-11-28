from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produkty', '0016_migrate_task_to_zadanie'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Task',
        ),
    ]
