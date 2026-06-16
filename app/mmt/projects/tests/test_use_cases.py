from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from mmt.projects.exceptions import ProjectError, ProjectPathError
from mmt.projects.models import Project
from mmt.projects.use_cases import create_project, update_project_title, delete_project

User = get_user_model()


class ProjectUseCaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='bob', password='password', email='bob@example.com'
        )

    # create_project
    def test_create_project_usecase_success(self):
        """create_project returns (True, project) is project can be created."""
        success, project = create_project(
            title='Dummy', description='Some dummy project.', user=self.user
        )

        self.assertTrue(success)
        self.assertEqual(project.title, 'Dummy')
        self.assertEqual(project.description, 'Some dummy project.')
        self.assertEqual(project.user_id, self.user.id)
        self.assertIsNotNone(project.id)

        project_directory = project.project_directory
        upload_directory = project_directory / 'upload'
        download_directory = project_directory / 'download'
        self.assertTrue(project_directory.exists(), 'Project directory was created.')
        self.assertTrue(upload_directory.exists(), 'Upload directory was created.')
        self.assertTrue(download_directory.exists(), 'Download directory was created.')

    def test_create_project_usecase_failure(self):
        """create_project returns (False, None) if creation fails."""
        success, project = create_project(
            description='Description, but no user or title'
        )

        self.assertFalse(success)
        self.assertIsNone(project)

    # update_project_title
    def test_update_project_title_success(self):
        """update_project_title renames the directory and persists pending changes."""
        _, project = create_project(
            title='Dummy', description='Some dummy project.', user=self.user
        )

        # Other pending changes on the instance should be saved along with the title.
        project.description = 'Some new dummy project.'
        update_project_title(project, 'NewDummy')

        project.refresh_from_db()
        self.assertEqual(project.title, 'NewDummy')
        self.assertEqual(project.description, 'Some new dummy project.')
        self.assertTrue(
            project.project_directory.exists(), 'Project directory was renamed.'
        )

    def test_update_project_title_invalid(self):
        """update_project_title raises ValidationError and changes nothing for an invalid title."""
        _, project = create_project(
            title='Dummy', description='Some dummy project.', user=self.user
        )
        old_project_directory = project.project_directory

        with self.assertRaises(ValidationError):
            update_project_title(project, '')

        self.assertEqual(project.title, 'Dummy')
        self.assertTrue(
            old_project_directory.exists(),
            'Project directory has not been renamed.',
        )

    @mock.patch('mmt.projects.use_cases.rename_directory')
    def test_update_project_title_directory_failure(self, rename_directory_mock):
        """update_project_title raises ProjectError and does not save if renaming fails."""
        rename_directory_mock.side_effect = FileNotFoundError('Directory not found')
        _, project = create_project(
            title='Dummy', description='Some dummy project.', user=self.user
        )
        old_project_directory = project.project_directory

        with self.assertRaises(ProjectError):
            update_project_title(project, 'Dummy2')

        self.assertEqual(project.title, 'Dummy', 'Field did not change')
        self.assertEqual(Project.objects.get(pk=project.pk).title, 'Dummy')
        self.assertTrue(
            old_project_directory.exists(),
            'Project directory has not been renamed.',
        )

    # delete_project
    def test_delete_project_usecase_success(self):
        """delete_project removes the project and its directories."""
        _, project = create_project(
            title='Dummy', description='Some dummy description', user=self.user
        )

        # Add some dummy files to project directory.
        project_directory = project.project_directory
        upload_directory = project_directory / 'upload'
        download_directory = project_directory / 'download'
        dummy_uploaded_file_path = upload_directory / 'temp_uploaded_file.mp4'
        with open(dummy_uploaded_file_path, 'w') as f:
            f.write('Just some dummy text.')
        dummy_downloaded_file_path = download_directory / 'temp_downloadable_file.mp4'
        with open(dummy_downloaded_file_path, 'w') as f:
            f.write('Just some dummy text.')

        delete_project(project)

        self.assertFalse(project_directory.exists())
        self.assertEqual(Project.objects.count(), 0)

    def test_delete_project_usecase_path_escape(self):
        """delete_project refuses and changes nothing if the directory escapes the user files dir."""
        _, project = create_project(
            title='Dummy', description='Some dummy description', user=self.user
        )

        with mock.patch.object(
            Project, 'project_directory', new_callable=mock.PropertyMock
        ) as project_directory_mock:
            project_directory_mock.return_value = Path('/etc')

            with self.assertRaises(ProjectPathError):
                delete_project(project)

        self.assertEqual(Project.objects.count(), 1)
