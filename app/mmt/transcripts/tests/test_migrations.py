import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

BEFORE_RENAME = ('transcripts', '0006_transcriptionjob')
AFTER_RENAME = ('transcripts', '0007_rename_mention_label_to_type')
BEFORE_ALIAS_REMOVAL = ('transcripts', '0008_entity_extraction_job')
AFTER_ALIAS_REMOVAL = ('transcripts', '0009_remove_entity_aliases')


def migrate_to(target):
    executor = MigrationExecutor(connection)
    executor.migrate([target])


@pytest.fixture(autouse=True)
def migrate_back_to_the_latest_state(transactional_db):
    yield
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.fixture
def make_transcript(transactional_db):
    user = get_user_model().objects.create_user(
        username='alice', password='password', terms_accepted_version=1
    )
    uploaded_file = UploadedFile.objects.create(
        project=create_project(title='Project', user=user),
        filename='file.mp4',
        original_filename='file.mp4',
    )

    def factory(mentions):
        return Transcript.objects.create(
            label='Interview',
            content={'format': 'mmt-transcript', 'mentions': mentions},
            uploaded_file=uploaded_file,
        )

    return factory


def test_the_migration_renames_label_to_type_in_every_mention(make_transcript):
    migrate_to(BEFORE_RENAME)
    first = make_transcript(
        {
            'men_1': {'label': 'PER', 'score': 0.9, 'entityId': None},
            'men_2': {'label': 'LOC', 'score': 0.8},
        }
    )
    second = make_transcript({'men_3': {'label': 'ORG'}})

    migrate_to(AFTER_RENAME)

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.content['mentions'] == {
        'men_1': {'type': 'PER', 'score': 0.9, 'entityId': None},
        'men_2': {'type': 'LOC', 'score': 0.8},
    }
    assert second.content['mentions'] == {'men_3': {'type': 'ORG'}}


def test_the_reverse_migration_renames_type_back_to_label(make_transcript):
    transcript = make_transcript({'men_1': {'type': 'DATE', 'score': 0.7}})

    migrate_to(BEFORE_RENAME)
    transcript.refresh_from_db()
    reversed_mentions = transcript.content['mentions']
    migrate_to(AFTER_RENAME)

    assert reversed_mentions == {'men_1': {'label': 'DATE', 'score': 0.7}}


def test_the_migration_leaves_content_without_mentions_untouched(make_transcript):
    migrate_to(BEFORE_RENAME)
    transcript = make_transcript({})
    Transcript.objects.filter(pk=transcript.pk).update(content={'segments': []})

    migrate_to(AFTER_RENAME)

    transcript.refresh_from_db()
    assert transcript.content == {'segments': []}


def store_content(transcript, content):
    Transcript.objects.filter(pk=transcript.pk).update(content=content)


def test_the_migration_removes_aliases_from_every_entity(make_transcript):
    migrate_to(BEFORE_ALIAS_REMOVAL)
    transcript = make_transcript({})
    store_content(
        transcript,
        {
            'entities': {
                'ent_1': {
                    'name': 'Angela Merkel',
                    'type': 'PER',
                    'aliases': ['Merkel'],
                },
                'ent_2': {'name': 'Berlin', 'type': 'LOC', 'wikidataId': 'Q64'},
            }
        },
    )

    migrate_to(AFTER_ALIAS_REMOVAL)

    transcript.refresh_from_db()
    assert transcript.content == {
        'entities': {
            'ent_1': {'name': 'Angela Merkel', 'type': 'PER'},
            'ent_2': {'name': 'Berlin', 'type': 'LOC', 'wikidataId': 'Q64'},
        }
    }


def test_the_reverse_migration_adds_an_empty_alias_list(make_transcript):
    transcript = make_transcript({})
    store_content(
        transcript, {'entities': {'ent_1': {'name': 'Berlin', 'type': 'LOC'}}}
    )

    migrate_to(BEFORE_ALIAS_REMOVAL)
    transcript.refresh_from_db()
    reversed_content = transcript.content
    migrate_to(AFTER_ALIAS_REMOVAL)

    assert reversed_content == {
        'entities': {'ent_1': {'name': 'Berlin', 'type': 'LOC', 'aliases': []}}
    }


def test_the_alias_migration_leaves_content_without_entities_untouched(
    make_transcript,
):
    migrate_to(BEFORE_ALIAS_REMOVAL)
    transcript = make_transcript({})
    store_content(transcript, {'segments': []})

    migrate_to(AFTER_ALIAS_REMOVAL)

    transcript.refresh_from_db()
    assert transcript.content == {'segments': []}
