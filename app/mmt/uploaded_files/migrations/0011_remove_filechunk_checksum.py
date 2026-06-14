from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('uploaded_files', '0010_uploadedfile_original_filename'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filechunk',
            name='checksum',
        ),
    ]
