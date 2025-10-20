from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0009_project_downloadable_files_count"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ServiceRequest",
            new_name="ProcessingRequest",
        ),
    ]
