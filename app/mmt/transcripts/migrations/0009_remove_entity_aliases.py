from django.db import migrations


def _change_entities(apps, change):
    """Apply ``change`` to every entity of every transcript."""
    Transcript = apps.get_model('transcripts', 'Transcript')
    for transcript in Transcript.objects.only('content').iterator():
        content = transcript.content
        entities = content.get('entities') if isinstance(content, dict) else None
        if not isinstance(entities, dict):
            continue
        changed = False
        for entity in entities.values():
            changed = change(entity) or changed
        if changed:
            transcript.save(update_fields=['content'])


def _remove_aliases(entity):
    if 'aliases' not in entity:
        return False
    del entity['aliases']
    return True


def _add_empty_aliases(entity):
    if 'aliases' in entity:
        return False
    entity['aliases'] = []
    return True


def remove_aliases(apps, schema_editor):
    _change_entities(apps, _remove_aliases)


def add_empty_aliases(apps, schema_editor):
    _change_entities(apps, _add_empty_aliases)


class Migration(migrations.Migration):
    dependencies = [
        ('transcripts', '0008_entity_extraction_job'),
    ]

    operations = [
        migrations.RunPython(remove_aliases, add_empty_aliases),
    ]
