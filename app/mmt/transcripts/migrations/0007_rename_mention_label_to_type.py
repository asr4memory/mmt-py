from django.db import migrations


def _rename_mention_key(apps, old, new):
    """Rename the key ``old`` to ``new`` in every mention of every transcript."""
    Transcript = apps.get_model('transcripts', 'Transcript')
    for transcript in Transcript.objects.only('content').iterator():
        content = transcript.content
        mentions = content.get('mentions') if isinstance(content, dict) else None
        if not isinstance(mentions, dict):
            continue
        renamed = False
        for mention in mentions.values():
            if old in mention:
                mention[new] = mention.pop(old)
                renamed = True
        if renamed:
            transcript.save(update_fields=['content'])


def rename_label_to_type(apps, schema_editor):
    _rename_mention_key(apps, 'label', 'type')


def rename_type_to_label(apps, schema_editor):
    _rename_mention_key(apps, 'type', 'label')


class Migration(migrations.Migration):
    dependencies = [
        ('transcripts', '0006_transcriptionjob'),
    ]

    operations = [
        migrations.RunPython(rename_label_to_type, rename_type_to_label),
    ]
