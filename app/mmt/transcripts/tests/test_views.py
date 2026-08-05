import json
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase

from mmt.projects.use_cases import create_project
from mmt.transcripts.models import Transcript
from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


def valid_mmt_content():
    return {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': [{'id': 'spk_1', 'name': 'Alice', 'color': '#5b9bd5'}],
        'entities': {},
        'segments': [
            {
                'id': 'seg_1',
                'start': 0.0,
                'end': 4.2,
                'speakerId': 'spk_1',
                'words': [
                    {
                        'id': 'wrd_1',
                        'start': 0.0,
                        'end': 0.3,
                        'word': 'Hi',
                        'score': 1.0,
                        'speakerId': 'spk_1',
                    }
                ],
            }
        ],
    }


class TranscriptViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        with open(Path(__file__).parent / 'transcript_sample.json') as f:
            cls.transcript_data = json.load(f)

        cls.alice = User.objects.create_user(
            username='alice',
            password='password',
            email='alice@example.com',
            terms_accepted_version=1,
        )
        cls.bob = User.objects.create_user(
            username='bob',
            password='password',
            email='bob@example.com',
            terms_accepted_version=1,
        )
        cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        cls.transcript = Transcript.objects.create(
            label='Test transcript',
            content=cls.transcript_data,
            uploaded_file=cls.uploaded_file,
        )

        uploaded_file_perms = [
            Permission.objects.get(codename='view_uploadedfile'),
            Permission.objects.get(codename='add_uploadedfile'),
            Permission.objects.get(codename='change_uploadedfile'),
            Permission.objects.get(codename='delete_uploadedfile'),
        ]
        transcript_perms = [
            Permission.objects.get(codename='view_transcript'),
            Permission.objects.get(codename='add_transcript'),
            Permission.objects.get(codename='change_transcript'),
            Permission.objects.get(codename='delete_transcript'),
        ]
        cls.alice.user_permissions.add(*uploaded_file_perms, *transcript_perms)
        cls.bob.user_permissions.add(*uploaded_file_perms, *transcript_perms)

    # Detail view
    def test_detail_view(self):
        """Detail view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/')
        self.assertContains(response, '<h1>Test transcript</h1>', html=True)

    def test_detail_view_shows_delete_button(self):
        """Detail view shows the delete button to a user with delete permission."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/')

        self.assertContains(response, 'data-testid="delete-button"')

    def test_detail_view_logged_out(self):
        """Detail view redirects if user is not logged in."""
        response = self.client.get(f'/transcripts/{self.transcript.id}/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/',
        )

    def test_detail_view_other_user(self):
        """Detail view of another user is not visible."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Edit view
    def test_edit_view(self):
        """Edit view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_view_logged_out(self):
        """Edit view redirects if user is not logged in."""
        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/edit/',
        )

    def test_edit_view_other_user(self):
        """Edit view of another user is not visible."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/edit/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # JSON view
    def test_json_view(self):
        """JSON view renders correctly."""
        self.client.login(username='alice', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/json/')
        self.assertDictEqual(response.json(), self.transcript_data)

    def test_json_view_logged_out(self):
        """JSON view sends FORBIDDEN status if user is not logged in."""
        response = self.client.get(
            f'/transcripts/{self.transcript.id}/json/',
            headers=dict(Accept='application/json'),
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_json_view_other_user(self):
        """JSON view sends NOT_FOUND status if another user is logged in."""
        self.client.login(username='bob', password='password')

        response = self.client.get(f'/transcripts/{self.transcript.id}/json/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_json_view_nonexistent(self):
        """JSON view sends NOT_FOUND status for a nonexistent transcript."""
        self.client.login(username='alice', password='password')

        response = self.client.get('/transcripts/99999/json/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Update transcript (JSON)
    def test_update_transcript_request(self):
        """Update transcript is successful."""
        self.client.login(username='alice', password='password')

        content = valid_mmt_content()
        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': content},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertJSONEqual(
            response.content, {'message': 'Transcript updated successfully.'}
        )
        self.transcript.refresh_from_db()
        self.assertEqual(self.transcript.content, content)

    def test_update_transcript_error_handling(self):
        """Update transcript error handling."""
        self.client.login(username='alice', password='password')

        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(response.content, {'message': 'content is required.'})

    def test_update_transcript_invalid_content(self):
        """Update transcript rejects content that is not a valid mmt-transcript."""
        self.client.login(username='alice', password='password')

        content = valid_mmt_content()
        del content['speakers']

        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': content},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        body = response.json()
        self.assertEqual(body['message'], 'The transcript is not valid.')
        self.assertTrue(body['errors'])
        self.transcript.refresh_from_db()
        self.assertEqual(self.transcript.content, self.transcript_data)

    def test_update_transcript_logged_out(self):
        """Update transcript returns error if logged out."""
        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': '{"segments": []}'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_update_transcript_other_user(self):
        """Update transcript not accessible by another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(
            f'/transcripts/{self.transcript.id}/update/',
            {'content': '{"segments": []}'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete view
    def test_delete_view(self):
        """Delete view works properly."""
        self.client.login(username='alice', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')

        self.assertRedirects(response, f'/uploaded-files/{self.uploaded_file.id}/')
        self.assertMessages(
            response, [Message(level=25, message='Transcript deleted successfully.')]
        )

    @mock.patch.object(Transcript, 'delete', side_effect=Exception)
    def test_delete_view_failure(self, delete_mock):
        """Delete view returns 500 if deletion fails."""
        self.client.login(username='alice', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')

        self.assertEqual(response.status_code, 500)

    def test_delete_view_logged_out(self):
        """Delete transcript view redirects if not logged in."""
        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')
        self.assertRedirects(
            response, f'/accounts/login/?next=/transcripts/{self.transcript.id}/delete/'
        )

    def test_delete_view_other_user(self):
        """Delete transcript view does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(f'/transcripts/{self.transcript.id}/delete/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class EnrichTranscriptViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user(
            username='alice_enrich',
            password='password',
            email='alice_enrich@example.com',
            terms_accepted_version=1,
        )
        cls.bob = User.objects.create_user(
            username='bob_enrich',
            password='password',
            email='bob_enrich@example.com',
            terms_accepted_version=1,
        )
        cls.project = create_project(title='Test project', user=cls.alice)
        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='interview.mp3',
            media_type='audio/mpeg',
        )
        cls.transcript = Transcript.objects.create(
            label='Interview',
            content={'segments': []},
            uploaded_file=cls.uploaded_file,
        )

        perms = [
            Permission.objects.get(codename='view_transcript'),
            Permission.objects.get(codename='add_transcript'),
            Permission.objects.get(codename='change_transcript'),
            Permission.objects.get(codename='view_uploadedfile'),
        ]
        cls.alice.user_permissions.add(*perms)
        cls.bob.user_permissions.add(*perms)

    @mock.patch('mmt.transcripts.views.enrich_transcript')
    def test_enrich_view(self, mock_task):
        """Enrich view dispatches the task, redirects, and shows a message.
        Without a batching field it defaults to speaker turns."""
        self.client.login(username='alice_enrich', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/enrich/')

        mock_task.delay.assert_called_once_with(self.transcript.pk, 'turns')
        self.assertRedirects(response, f'/uploaded-files/{self.uploaded_file.pk}/')
        self.assertMessages(
            response, [Message(level=20, message='Enrichment started.')]
        )

    @mock.patch('mmt.transcripts.views.enrich_transcript')
    def test_enrich_view_segment_batching(self, mock_task):
        self.client.login(username='alice_enrich', password='password')

        self.client.post(
            f'/transcripts/{self.transcript.id}/enrich/',
            {'batching': 'segments'},
        )

        mock_task.delay.assert_called_once_with(self.transcript.pk, 'segments')

    @mock.patch('mmt.transcripts.views.enrich_transcript')
    def test_enrich_view_rejects_unknown_batching(self, mock_task):
        self.client.login(username='alice_enrich', password='password')

        response = self.client.post(
            f'/transcripts/{self.transcript.id}/enrich/',
            {'batching': 'bogus'},
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        mock_task.delay.assert_not_called()

    def test_enrich_view_logged_out(self):
        """Enrich view redirects to login if not authenticated."""
        response = self.client.post(f'/transcripts/{self.transcript.id}/enrich/')

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{self.transcript.id}/enrich/',
        )

    def test_enrich_view_other_user(self):
        """Enrich view returns 404 for a transcript belonging to another user."""
        self.client.login(username='bob_enrich', password='password')

        response = self.client.post(f'/transcripts/{self.transcript.id}/enrich/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch('mmt.transcripts.views.enrich_transcript')
    def test_enrich_view_requires_change_permission(self, mock_task):
        """Enrich view requires the change_transcript permission."""
        charlie = User.objects.create_user(
            username='charlie_enrich',
            password='password',
            email='charlie_enrich@example.com',
            terms_accepted_version=1,
        )
        charlie_project = create_project(title='Charlie project', user=charlie)
        charlie_file = UploadedFile.objects.create(
            project=charlie_project,
            filename='interview.mp3',
            media_type='audio/mpeg',
        )
        charlie_transcript = Transcript.objects.create(
            label='Interview',
            content={'segments': []},
            uploaded_file=charlie_file,
        )
        charlie.user_permissions.add(
            Permission.objects.get(codename='view_transcript'),
            Permission.objects.get(codename='add_transcript'),
        )
        self.client.login(username='charlie_enrich', password='password')

        response = self.client.post(f'/transcripts/{charlie_transcript.id}/enrich/')

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/transcripts/{charlie_transcript.id}/enrich/',
            fetch_redirect_response=False,
        )
        mock_task.delay.assert_not_called()


@pytest.fixture
def editable_transcript(db):
    """A transcript its owner may change, and that owner."""
    user = User.objects.create_user(
        username='dora',
        password='password',
        email='dora@example.com',
        terms_accepted_version=1,
    )
    user.user_permissions.add(
        Permission.objects.get(codename='view_transcript'),
        Permission.objects.get(codename='change_transcript'),
    )
    project = create_project(title='Test project', user=user)
    uploaded_file = UploadedFile.objects.create(
        project=project,
        filename='interview.mp3',
        original_filename='interview.mp3',
        media_type='audio/mpeg',
    )
    transcript = Transcript.objects.create(
        label='Interview',
        content=valid_mmt_content(),
        uploaded_file=uploaded_file,
    )
    return user, transcript


def content_with_entity():
    """Content whose single mention is linked to a single entity."""
    content = valid_mmt_content()
    content['mentions'] = {'men_1': {'label': 'PER', 'entityId': 'ent_1'}}
    content['entities'] = {
        'ent_1': {'name': 'Alice', 'type': 'PER', 'aliases': [], 'wikidataId': None}
    }
    content['segments'][0]['words'][0]['mentionId'] = 'men_1'
    return content


def post_content(client, transcript, content):
    return client.post(
        f'/transcripts/{transcript.id}/update/',
        {'content': content},
        content_type='application/json',
    )


def test_update_accepts_a_register(client, editable_transcript):
    user, transcript = editable_transcript
    client.force_login(user)
    content = content_with_entity()

    response = post_content(client, transcript, content)

    assert response.status_code == HTTPStatus.OK
    transcript.refresh_from_db()
    assert transcript.content == content


def test_update_rejects_a_dangling_entity_id(client, editable_transcript):
    user, transcript = editable_transcript
    client.force_login(user)
    content = content_with_entity()
    content['mentions']['men_1']['entityId'] = 'ent_ghost'

    response = post_content(client, transcript, content)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    transcript.refresh_from_db()
    assert transcript.content == valid_mmt_content()


def test_update_rejects_an_orphaned_entity(client, editable_transcript):
    user, transcript = editable_transcript
    client.force_login(user)
    content = content_with_entity()
    content['mentions']['men_1']['entityId'] = None

    response = post_content(client, transcript, content)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    transcript.refresh_from_db()
    assert transcript.content == valid_mmt_content()
