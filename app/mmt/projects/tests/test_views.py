from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase
from django.utils import timezone

from mmt.my_account.models import FeatureFlag
from mmt.projects.exceptions import ProjectError
from mmt.projects.models import ProcessingRequest, Project
from mmt.projects.use_cases import create_project
from django.conf import settings

from mmt.uploaded_files.models import UploadedFile

User = get_user_model()


class ProjectViewTests(TestCase, MessagesTestMixin):
    @classmethod
    def setUpTestData(cls):
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

        _, cls.project = create_project(title='Test project', user=cls.alice)

        cls.uploaded_file = UploadedFile.objects.create(
            project=cls.project,
            filename='test_file.mp4',
            original_filename='test_file.mp4',
            has_file=True,
            size=20000,
            media_type='video/mp4',
        )
        cls.processing_request = ProcessingRequest.objects.create(
            project=cls.project,
            description='Put on platform.',
            make_available_on_platform=True,
        )

        perm1 = Permission.objects.get(codename='view_uploadedfile')
        perm2 = Permission.objects.get(codename='add_uploadedfile')
        perm3 = Permission.objects.get(codename='view_processingrequest')
        perm4 = Permission.objects.get(codename='add_processingrequest')
        perm5 = Permission.objects.get(codename='delete_processingrequest')
        cls.alice.user_permissions.add(perm1, perm2, perm3, perm4, perm5)
        cls.bob.user_permissions.add(perm1, perm2, perm3, perm4, perm5)

    # Project index
    def test_project_index_page_alice(self):
        """Shows the projects of the user."""
        self.client.login(username='alice', password='password')

        response = self.client.get('/projects/')
        soup = BeautifulSoup(response.content, 'html.parser')
        project_card = soup.find(attrs={'data-testid': 'project-card'})
        self.assertIn('Test project', project_card.get_text())

        new_project_link = soup.find(attrs={'data-testid': 'new-project-link'})
        self.assertIsNotNone(new_project_link)

    def test_project_index_page_bob(self):
        """Does not show projects of other users."""
        self.client.login(username='bob', password='password')

        response = self.client.get('/projects/')
        soup = BeautifulSoup(response.content, 'html.parser')
        project_card = soup.find(attrs={'data-testid': 'project-card'})

        self.assertIsNone(project_card)

    def test_project_index_logged_out(self):
        """Project index redirects if not logged in."""
        response = self.client.get('/projects/')

        self.assertRedirects(response, '/accounts/login/?next=/projects/')

    # Project detail
    def test_project_detail_page(self):
        """Project detail page renders correctly."""
        self.client.login(username='alice', password='password')

        project = Project.objects.first()

        response = self.client.get(f'/projects/{project.id}/')
        soup = BeautifulSoup(response.content, 'html.parser')

        project_name = soup.find(attrs={'data-testid': 'project-name'})
        self.assertIn('Test project', project_name.get_text())

        upload_files_link = soup.find(attrs={'data-testid': 'upload-files-link'})
        self.assertIsNotNone(upload_files_link)

    def test_project_detail_page_no_upload_permission(self):
        """Displays profile page link if upload permission is missing."""
        alice = self.alice
        alice.user_permissions.clear()
        self.client.login(username='alice', password='password')
        project = Project.objects.first()

        response = self.client.get(f'/projects/{project.id}/')
        soup = BeautifulSoup(response.content, 'html.parser')

        upload_files_link = soup.find(attrs={'data-testid': 'upload-files-link'})
        self.assertIsNone(upload_files_link)
        profile_page_link = soup.find(attrs={'data-testid': 'profile-page-link'})
        self.assertIn('Visit profile', profile_page_link.get_text())

    def test_project_detail_page_upload_permission_requested(self):
        """Displays message if upload permission has been requested."""
        alice = self.alice
        alice.user_permissions.clear()
        alice.upload_permission_requested_at = timezone.now()
        alice.save()
        self.client.login(username='alice', password='password')
        project = Project.objects.first()

        response = self.client.get(f'/projects/{project.id}/')
        self.assertContains(response, f'You have requested upload permission.')

    def test_project_page_logged_out(self):
        """Redirects if user is not logged in."""
        project = Project.objects.first()
        response = self.client.get(f'/projects/{project.id}/')

        self.assertRedirects(response, f'/accounts/login/?next=/projects/{project.id}/')

    def test_project_detail_page_another_user(self):
        """Project detail page of another user is not visible."""
        self.client.login(username='bob', password='password')
        project = Project.objects.first()

        response = self.client.get(f'/projects/{project.id}/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_project_detail_page_missing_directory(self):
        """Returns 500 and error template when the project directory is missing."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()

        with mock.patch(
            'mmt.projects.views.get_files_with_info', side_effect=FileNotFoundError
        ):
            response = self.client.get(f'/projects/{project.id}/')

        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertTemplateUsed(response, 'projects/project_detail_error.html')

    # New project
    def test_new_project(self):
        """New project page renders correctly."""
        self.client.login(username='bob', password='password')
        response = self.client.get('/projects/create/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'create-project-form'})
        self.assertIsNotNone(form)

    def test_new_project_redirect(self):
        """New project page redirects if not logged in."""
        response = self.client.get('/projects/create/')

        self.assertRedirects(response, '/accounts/login/?next=/projects/create/')

    def test_new_project_post_request(self):
        """New project is created."""
        self.client.login(username='bob', password='password')

        response = self.client.post(
            '/projects/create/',
            {'title': "Bob's project", 'description': 'Test description'},
        )

        project = Project.objects.get(user=self.bob)
        self.assertRedirects(response, f'/projects/{project.id}/')
        self.assertEqual(project.title, "Bob's project")
        self.assertEqual(project.description, 'Test description')
        self.assertMessages(
            response, [Message(level=25, message='Project created successfully.')]
        )

    def test_new_project_post_redirect(self):
        """New project post request redirects if not logged in."""
        response = self.client.post(
            '/projects/create/',
            {'title': "Bob's project", 'description': 'Test description'},
        )
        self.assertRedirects(response, '/accounts/login/?next=/projects/create/')

    # Project settings
    def test_project_settings(self):
        """Project settings page renders correctly."""
        self.client.login(username='alice', password='password')
        response = self.client.get(f'/projects/{self.project.id}/settings/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'edit-project-form'})
        self.assertIsNotNone(form)

        delete_button = soup.find(attrs={'data-testid': 'delete-project-button'})
        self.assertIsNotNone(delete_button)

    def test_project_settings_redirect(self):
        """Project settings page redirects if not logged in."""
        response = self.client.get(f'/projects/{self.project.id}/settings/')

        self.assertRedirects(
            response, f'/accounts/login/?next=/projects/{self.project.id}/settings/'
        )

    def test_project_settings_other_user(self):
        """Project settings page does not render for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.get(f'/projects/{self.project.id}/settings/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Update project post request.
    @mock.patch('mmt.projects.views.update_project_title')
    def test_project_settings_post_request_success(self, update_project_title_mock):
        """Project settings post request is successful."""
        update_project_title_mock.return_value = None
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/settings/',
            {'title': 'New name', 'description': 'New description'},
        )

        self.assertRedirects(response, f'/projects/{self.project.id}/')
        self.assertMessages(
            response, [Message(level=25, message='Project updated successfully.')]
        )

    @mock.patch('mmt.projects.views.update_project_title')
    def test_project_settings_post_request_failure(self, update_project_title_mock):
        """Project settings post request fails."""
        update_project_title_mock.side_effect = ProjectError('boom')
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/settings/',
            {'title': 'New name', 'description': 'New description'},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertMessages(
            response, [Message(level=30, message='Project update failed.')]
        )

    def test_project_settings_post_redirect(self):
        """Project settings post request redirects if not logged in."""
        response = self.client.post(
            f'/projects/{self.project.id}/settings/',
            {'title': 'New name', 'description': 'New description'},
        )
        self.assertRedirects(
            response, f'/accounts/login/?next=/projects/{self.project.id}/settings/'
        )

    def test_project_settings_post_other_user(self):
        """Project settings post request does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/settings/',
            {'title': 'New name', 'description': 'New description'},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete project
    @mock.patch('mmt.projects.views.delete_project')
    def test_delete_project_post_request_success(self, delete_project_usecase_mock):
        """Delete project is successful."""
        delete_project_usecase_mock.return_value = None
        self.client.login(username='alice', password='password')
        response = self.client.post(f'/projects/{self.project.id}/delete/')

        self.assertRedirects(response, '/projects/')
        self.assertMessages(
            response, [Message(level=25, message='Project deleted successfully.')]
        )
        delete_project_usecase_mock.assert_called_once()

    @mock.patch('mmt.projects.views.delete_project')
    def test_delete_project_post_request_failure(self, delete_project_usecase_mock):
        """Delete project fails."""
        delete_project_usecase_mock.side_effect = ProjectError('boom')
        self.client.login(username='alice', password='password')
        response = self.client.post(f'/projects/{self.project.id}/delete/')

        self.assertEqual(response.status_code, 500)
        delete_project_usecase_mock.assert_called_once()

    def test_delete_project_post_redirect(self):
        """Delete project post request redirects if not logged in."""
        response = self.client.post(f'/projects/{self.project.id}/delete/')
        self.assertRedirects(
            response, f'/accounts/login/?next=/projects/{self.project.id}/delete/'
        )

    def test_delete_project_post_other_user(self):
        """Delete project post request does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(f'/projects/{self.project.id}/delete/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Upload files page
    def test_upload_files_page(self):
        """Upload files page renders correctly."""
        self.client.login(username='alice', password='password')

        project = Project.objects.first()
        response = self.client.get(f'/projects/{project.id}/upload/')

        self.assertContains(response, '<h1>Upload Files</h1>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'upload-files-form'})
        self.assertIsNotNone(form)
        project_id_in_form = int(form.attrs['data-project-id'])
        self.assertEqual(project_id_in_form, project.id)

    def test_upload_files_redirect(self):
        """Upload files page redirects if logged out."""
        project = Project.objects.first()
        response = self.client.get(f'/projects/{project.id}/upload/')

        self.assertRedirects(
            response, f'/accounts/login/?next=/projects/{project.id}/upload/'
        )

    def test_upload_files_other_user(self):
        """Upload files page not accessible by another user."""
        self.client.login(username='bob', password='password')
        project = Project.objects.first()
        response = self.client.get(f'/projects/{project.id}/upload/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_upload_context_chunked_upload_disabled(self):
        """chunked_upload is False when CHUNKED_UPLOAD flag is not set."""
        self.client.login(username='alice', password='password')
        response = self.client.get(f'/projects/{self.project.id}/upload/')

        self.assertFalse(response.context['chunked_upload'])

    def test_upload_context_chunked_upload_enabled(self):
        """chunked_upload is True when CHUNKED_UPLOAD flag is set."""
        FeatureFlag.objects.create(
            user=self.alice, name=FeatureFlag.Name.CHUNKED_UPLOAD
        )
        self.client.login(username='alice', password='password')
        response = self.client.get(f'/projects/{self.project.id}/upload/')

        self.assertTrue(response.context['chunked_upload'])

    # Create uploaded file view (JSON)
    def test_create_uploaded_file_view(self):
        """Uploaded file is created."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/create-file/',
            {'filename': 'new_file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.get(filename='new_file.mp4')
        expected = {
            'id': uploaded_file.id,
            'filename': 'new_file.mp4',
            'chunk_size': settings.MMT_UPLOAD_CHUNK_SIZE,
        }
        self.assertJSONEqual(response.content, expected)

    def test_create_uploaded_file_missing_fields(self):
        """Missing fields are reported together."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/create-file/',
            {'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        data = response.json()
        self.assertIn('filename', data['errors'])

    def test_create_uploaded_file_invalid_json(self):
        """Non-JSON body returns 400."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/create-file/',
            'not json',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertJSONEqual(response.content, {'message': 'Invalid JSON'})

    @mock.patch('mmt.projects.views.get_filename_suffix', return_value='20000101103015')
    def test_create_uploaded_file_filename_exists(self, mock_suffix):
        """If filename exists within the project, a suffix is attached."""
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/create-file/',
            {'filename': 'test_file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.last()
        expected = {
            'id': uploaded_file.id,
            'filename': 'test_file.mp4.20000101103015',
            'chunk_size': settings.MMT_UPLOAD_CHUNK_SIZE,
        }
        self.assertJSONEqual(response.content, expected)

    def test_create_uploaded_file_no_conflict_stores_original_filename(self):
        """original_filename always stores the submitted filename."""
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/create-file/',
            {
                'filename': 'unique_file.mp4',
                'content_type': 'video/mp4',
                'size': 20000,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.get(filename='unique_file.mp4')
        self.assertEqual(uploaded_file.original_filename, 'unique_file.mp4')

    def test_create_uploaded_file_sanitizes_filename(self):
        """Filename is sanitized and original_filename stores the submitted value."""
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/create-file/',
            {'filename': 'my file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.get(filename='my_file.mp4')
        self.assertEqual(uploaded_file.original_filename, 'my file.mp4')

    @mock.patch('mmt.projects.views.get_filename_suffix', return_value='20000101103015')
    def test_create_uploaded_file_conflict_stores_original_filename(self, mock_suffix):
        """original_filename is set to the requested filename when a conflict causes a rename."""
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/create-file/',
            {'filename': 'test_file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        uploaded_file = UploadedFile.objects.get(
            filename='test_file.mp4.20000101103015'
        )
        self.assertEqual(uploaded_file.original_filename, 'test_file.mp4')

    def test_create_uploaded_file_logged_out(self):
        """Create uploaded file returns 403 if logged out."""
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/create-file/',
            {'filename': 'new_file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_create_uploaded_file_other_user(self):
        """Create uploaded file not accessible by another user."""
        self.client.login(username='bob', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/create-file/',
            {'filename': 'new_file.mp4', 'content_type': 'video/mp4', 'size': 20000},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Processing requests
    # Create processing request
    def test_create_processing_request_get(self):
        """Processing request form is shown."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/create/'
        )

        self.assertContains(response, '<h1>New Processing Request</h1>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'processing-request-form'})
        self.assertIsNotNone(form)

    def test_create_processing_request_get_logged_out(self):
        """Create processing request page redirects if logged out."""
        project = Project.objects.first()
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/create/'
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/projects/{project.id}/processing-requests/create/',
        )

    def test_create_processing_request_get_other_user(self):
        """Create processing request page is not accessible for another user."""
        self.client.login(username='bob', password='password')
        project = Project.objects.first()
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/create/'
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch('mmt.projects.tasks.send_new_processing_request_email.delay')
    def test_create_processing_request_post(self, send_email_mock):
        """Processing request is created."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/processing-requests/create/',
            {
                'description': 'Transcribe my file.',
                'uploaded_files': ['test_file.mp4'],
                'make_available_on_platform': True,
                'language': 'other',
            },
        )

        self.assertRedirects(response, f'/projects/{project.id}/')
        self.assertMessages(
            response,
            [Message(level=25, message='Processing request created successfully.')],
        )
        processing_request = ProcessingRequest.objects.get(
            description='Transcribe my file.'
        )
        self.assertIsNotNone(processing_request)
        send_email_mock.assert_called_once()

    def test_create_processing_request_uploaded_files(self):
        """Processing request without selected uploaded files is rejected."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/processing-requests/create/',
            {'description': 'Transcribe my file.'},
        )
        self.assertContains(response, 'This field is required.')

    def test_create_processing_request_actions(self):
        """Processing request without selecting actions is rejected."""
        self.client.login(username='alice', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/processing-requests/create/',
            {'description': 'Transcribe my file.', 'uploaded_files': ['test_file.mp4']},
        )
        self.assertContains(response, 'At least one action must be checked.')

    def test_create_processing_request_post_logged_out(self):
        """Processing request view redirects if logged out."""
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/processing-requests/create/',
            {'description': 'Transcribe my file.'},
        )
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/projects/{project.id}/processing-requests/create/',
        )

    def test_create_processing_request_post_other_user(self):
        """Processing request view does not work for another user."""
        self.client.login(username='bob', password='password')
        project = Project.objects.first()
        response = self.client.post(
            f'/projects/{project.id}/processing-requests/create/',
            {'description': 'Transcribe my file.'},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Processing request detail
    def test_processing_request_detail(self):
        """Processing request is shown."""
        self.client.login(username='alice', password='password')
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/{processing_request.id}/'
        )

        self.assertContains(
            response, f"<dd class='u-ll'>Put on platform.</dd>", html=True
        )
        soup = BeautifulSoup(response.content, 'html.parser')
        button = soup.find(attrs={'data-testid': 'delete-button'})
        self.assertIsNotNone(button)

    def test_processing_request_detail_accepted(self):
        """Delete button is not shown if the processing request is accepted."""
        self.client.login(username='alice', password='password')
        self.processing_request.status = ProcessingRequest.Status.ACCEPTED
        self.processing_request.save()
        response = self.client.get(
            f'/projects/{self.project.id}/processing-requests/{self.processing_request.id}/'
        )

        soup = BeautifulSoup(response.content, 'html.parser')
        button = soup.find(attrs={'data-testid': 'delete-button'})
        self.assertIsNone(button)

    def test_processing_request_detail_logged_out(self):
        """Processing request page redirects if logged out."""
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/{processing_request.id}/'
        )

        self.assertRedirects(
            response,
            f'/accounts/login/?next=/projects/{project.id}/processing-requests/{processing_request.id}/',
        )

    def test_processing_request_detail_other_user(self):
        """Processing request page is not accessible for another user."""
        self.client.login(username='bob', password='password')
        processing_request = ProcessingRequest.objects.first()
        project = processing_request.project
        response = self.client.get(
            f'/projects/{project.id}/processing-requests/{processing_request.id}/'
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Delete processing request
    def test_delete_processing_request_post_request(self):
        """Delete processing request is successful."""
        self.client.login(username='alice', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/processing-requests/{self.processing_request.id}/delete/'
        )

        self.assertRedirects(response, f'/projects/{self.project.id}/')
        self.assertEqual(ProcessingRequest.objects.count(), 0)
        self.assertMessages(
            response,
            [Message(level=25, message='Processing request deleted successfully.')],
        )

    def test_delete_processing_request_post_request_accepted(self):
        """Delete processing request is forbidden if the request is accepted."""
        self.client.login(username='alice', password='password')
        self.processing_request.status = ProcessingRequest.Status.ACCEPTED
        self.processing_request.save()
        response = self.client.post(
            f'/projects/{self.project.id}/processing-requests/{self.processing_request.id}/delete/'
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(ProcessingRequest.objects.count(), 1)

    def test_delete_processing_request_post_redirect(self):
        """Delete processing request post request redirects if not logged in."""
        response = self.client.post(
            f'/projects/{self.project.id}/processing-requests/{self.processing_request.id}/delete/'
        )
        self.assertRedirects(
            response,
            f'/accounts/login/?next=/projects/{self.project.id}/processing-requests/{self.processing_request.id}/delete/',
        )

    def test_delete_processing_request_post_other_user(self):
        """Delete processing request post request does not work for another user."""
        self.client.login(username='bob', password='password')
        response = self.client.post(
            f'/projects/{self.project.id}/processing-requests/{self.processing_request.id}/delete/'
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
