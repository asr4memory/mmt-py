"""Tests for the Transcript model's own validation.

``content`` carries a validator, so every ``full_clean()`` — the admin's change
form, the transcript form, any future ModelForm — rejects content that is not a
valid mmt-transcript document. ``Transcript.objects.create()`` still writes
whatever it is given; Django does not validate on save, and the ingest paths
validate before they get there.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()

# Whisper/whisperX output. The transcript form accepts this and normalizes it
# before the instance is built; the model itself does not.
WHISPER_CONTENT = {
    'language': 'de',
    'segments': [
        {
            'start': 0.0,
            'end': 0.3,
            'words': [{'word': 'Hi', 'start': 0.0, 'end': 0.3}],
        }
    ],
}


def valid_mmt_content():
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'language': 'de',
        'speakers': [{'id': 's1', 'name': 'Alice', 'color': '#5b9bd5'}],
        'mentions': {},
        'segments': [
            {
                'id': 'seg_1',
                'start': 0.0,
                'end': 0.3,
                'speakerId': 's1',
                'words': [
                    {
                        'id': 'wrd_1',
                        'start': 0.0,
                        'end': 0.3,
                        'word': 'Hi',
                        'score': 1.0,
                        'speakerId': 's1',
                        'mentionId': None,
                    }
                ],
            }
        ],
    }


@pytest.fixture
def uploaded_file(db):
    user = User.objects.create_user(
        username='alice',
        password='password',
        email='alice@example.com',
        terms_accepted_version=1,
    )
    return UploadedFile.objects.create(
        project=create_project(title='Test project', user=user),
        filename='interview.wav',
        original_filename='interview.wav',
        has_file=True,
        size=20000,
        media_type='audio/wav',
    )


def transcript_with(uploaded_file, content):
    return Transcript(label='Interview', content=content, uploaded_file=uploaded_file)


def test_valid_mmt_content_passes(uploaded_file):
    transcript_with(uploaded_file, valid_mmt_content()).full_clean()


def test_whisper_content_is_rejected(uploaded_file):
    transcript = transcript_with(uploaded_file, WHISPER_CONTENT)

    with pytest.raises(ValidationError) as error:
        transcript.full_clean()

    assert 'content' in error.value.error_dict


def test_invalid_mmt_content_is_rejected(uploaded_file):
    content = valid_mmt_content()
    del content['speakers']
    transcript = transcript_with(uploaded_file, content)

    with pytest.raises(ValidationError) as error:
        transcript.full_clean()

    assert 'content' in error.value.error_dict


def test_the_reason_is_reported(uploaded_file):
    content = valid_mmt_content()
    content['segments'][0]['speakerId'] = 'unknown'
    transcript = transcript_with(uploaded_file, content)

    with pytest.raises(ValidationError) as error:
        transcript.full_clean()

    assert any(
        'unknown speakerId' in message
        for message in error.value.error_dict['content'][0].messages
    )


def test_empty_content_is_rejected(uploaded_file):
    """The field's default is an empty dict, which is not a transcript."""
    transcript = transcript_with(uploaded_file, {})

    with pytest.raises(ValidationError) as error:
        transcript.full_clean()

    assert 'content' in error.value.error_dict


def test_create_does_not_validate(uploaded_file):
    """Django does not validate on save, so the ingest paths stay responsible
    for what they write. This is what lets the tests and the NER task build
    content directly."""
    transcript = Transcript.objects.create(
        label='Interview', content=WHISPER_CONTENT, uploaded_file=uploaded_file
    )

    transcript.refresh_from_db()
    assert transcript.content == WHISPER_CONTENT
