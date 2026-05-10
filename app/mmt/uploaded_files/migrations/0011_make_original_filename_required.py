from django.db import migrations, models


def backfill_original_filename(apps, schema_editor):
    UploadedFile = apps.get_model('uploaded_files', 'UploadedFile')
    UploadedFile.objects.filter(original_filename='').update(
        original_filename=models.F('filename')
    )


class Migration(migrations.Migration):
    dependencies = [
        ('uploaded_files', '0010_add_original_filename_to_uploaded_file'),
    ]

    operations = [
        migrations.RunPython(backfill_original_filename, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='uploadedfile',
            name='original_filename',
            field=models.CharField(max_length=255, verbose_name='Original filename'),
        ),
    ]
