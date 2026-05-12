from datetime import datetime, UTC
from http import HTTPStatus
from unittest import mock

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.base import Message
from django.contrib.messages.test import MessagesTestMixin
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

User = get_user_model()


class MyAccountViewTests(TestCase, MessagesTestMixin):
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
        perm1 = Permission.objects.get(codename='view_uploadedfile')
        perm2 = Permission.objects.get(codename='add_uploadedfile')
        cls.alice.user_permissions.add(perm1, perm2)

    def setUp(self):
        self.alice.refresh_from_db()
        self.bob.refresh_from_db()

    # Profile page
    def test_profile_page(self):
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/')

        self.assertContains(response, '<h1>Profile</h1>', html=True)
        self.assertContains(response, 'bob', html=True)
        self.assertContains(response, 'bob@example.com', html=True)
        self.assertContains(response, '<li>Download</li>', html=True)

    def test_profile_page_permission_request_button(self):
        "Permission is not shown, button is displayed."
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/')

        self.assertNotContains(response, '<li>Upload</li>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'request-permission-form'})
        self.assertIn('Request upload permission', form.get_text())

    def test_profile_page_permission_requested(self):
        "Once permission is requested, message is shown."
        self.bob.upload_permission_requested_at = timezone.now()
        self.bob.save()
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/')

        self.assertNotContains(response, '<li>Upload</li>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        message = soup.find(attrs={'data-testid': 'request-permission-message'})
        self.assertIn('Upload permission requested', message.get_text())
        form = soup.find(attrs={'data-testid': 'request-permission-form'})
        self.assertIsNone(form)

    def test_profile_page_permission_available(self):
        "Permission is shown if available, button not."
        self.client.login(username='alice', password='password')
        response = self.client.get('/account/profile/')

        self.assertContains(response, '<li>Upload</li>', html=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        form = soup.find(attrs={'data-testid': 'request-permission-form'})
        self.assertIsNone(form)

    def test_profile_page_context1(self):
        "Profile view some context tests."
        self.client.login(username='alice', password='password')
        response = self.client.get('/account/profile/')
        self.assertIsNone(response.context['terms_accepted_date'])
        self.assertFalse(response.context['show_dpa_section'])
        self.assertIsNone(response.context['dpa_accepted_date'])
        self.assertFalse(response.context['show_signed_dpa_link'])

    def test_profile_page_context2(self):
        "Profile view some more context tests."
        alice = self.alice
        alice.email = 'alice@external.com'
        alice.accept_terms()
        alice.accept_dpa()
        alice.save()
        self.client.login(username='alice', password='password')
        response = self.client.get('/account/profile/')

        self.assertIsInstance(response.context['terms_accepted_date'], datetime)
        self.assertTrue(response.context['show_dpa_section'])
        self.assertIsInstance(response.context['dpa_accepted_date'], datetime)
        self.assertFalse(response.context['show_signed_dpa_link'])

    def test_profile_page_redirect(self):
        "Profile page redirects if not logged in."
        response = self.client.get('/account/profile/')

        self.assertRedirects(response, '/accounts/login/?next=/account/profile/')

    # Edit profile page
    def test_edit_profile_page(self):
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/edit/')

        self.assertContains(response, '<h1>Edit profile</h1>', html=True)

    def test_edit_profile_page_redirect(self):
        response = self.client.get('/account/profile/edit/')

        self.assertRedirects(response, '/accounts/login/?next=/account/profile/edit/')

    def test_edit_profile_post_request(self):
        self.client.login(username='bob', password='password')

        response = self.client.post(
            '/account/profile/edit/', {'full_name': 'Bob Sanders', 'locale': 'de'}
        )
        self.assertRedirects(response, '/account/profile/')

        profile = self.bob.safe_profile
        self.assertEqual(profile.full_name, 'Bob Sanders')
        self.assertEqual(profile.locale, 'de')

    def test_edit_profile_post_logged_out(self):
        response = self.client.post(
            '/account/profile/edit/', {'full_name': 'Bob Sanders', 'locale': 'de'}
        )
        self.assertRedirects(response, '/accounts/login/?next=/account/profile/edit/')

    # Upload permission
    @mock.patch('mmt.my_account.tasks.send_upload_permission_request_email.delay')
    def test_post_upload_permission(self, send_email_mock):
        "Normal upload-permission post request."
        self.client.login(username='bob', password='password')
        response = self.client.post('/account/profile/upload-permission/')

        self.assertRedirects(response, '/account/profile/')
        self.assertMessages(
            response, [Message(level=25, message='Upload permission requested.')]
        )
        bob = User.objects.get(username='bob')
        self.assertIsNotNone(bob.upload_permission_requested_at)
        send_email_mock.assert_called_once()

    def test_get_upload_permission(self):
        "GET upload-permission request fails."
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/upload-permission/')

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_post_upload_permission_logged_out(self):
        response = self.client.post('/account/profile/upload-permission/')
        self.assertRedirects(
            response, '/accounts/login/?next=/account/profile/upload-permission/'
        )

    @mock.patch('mmt.my_account.tasks.send_upload_permission_request_email.delay')
    def test_post_upload_permission_already_requested(self, send_email_mock):
        "When already requested, redirect without sending the email again."
        self.bob.upload_permission_requested_at = timezone.now()
        self.bob.save()
        self.client.login(username='bob', password='password')

        response = self.client.post('/account/profile/upload-permission/')

        self.assertRedirects(response, '/account/profile/')
        send_email_mock.assert_not_called()

    # Accept terms page
    def test_accept_terms_page(self):
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/accept-terms/')

        self.assertContains(response, '<h1>Consent required</h1>', html=True)

    def test_accept_terms_page_redirect(self):
        response = self.client.get('/account/profile/accept-terms/')

        self.assertRedirects(
            response, '/accounts/login/?next=/account/profile/accept-terms/'
        )

    @override_settings(MMT_TERMS_VERSION=2)
    def test_accept_terms_get_context_terms_needed(self):
        "Context reflects that terms acceptance is required."
        self.client.login(username='bob', password='password')

        response = self.client.get('/account/profile/accept-terms/')

        self.assertTrue(response.context['show_accept_terms_part'])
        self.assertFalse(response.context['show_accept_dpa_part'])

    def test_accept_terms_get_context_dpa_needed(self):
        "Context reflects that DPA acceptance is required for external users."
        self.bob.email = 'bob@external.com'
        self.bob.save()
        self.client.login(username='bob', password='password')

        response = self.client.get('/account/profile/accept-terms/')

        self.assertFalse(response.context['show_accept_terms_part'])
        self.assertTrue(response.context['show_accept_dpa_part'])

    @override_settings(MMT_TERMS_VERSION=2)
    @mock.patch('mmt.my_account.views.create_dpa_pdf.delay')
    def test_accept_terms_post_request(self, create_pdf_mock):
        self.client.login(username='bob', password='password')

        response = self.client.post(
            '/account/profile/accept-terms/', {'accept_terms_field': True}
        )
        self.assertRedirects(response, '/')
        self.assertMessages(
            response,
            [Message(level=25, message='You agreed to the required documents.')],
        )
        self.bob.refresh_from_db()
        self.assertEqual(self.bob.terms_accepted_version, 2)
        create_pdf_mock.assert_not_called()

    @mock.patch('mmt.my_account.views.create_dpa_pdf.delay')
    def test_accept_terms_post_dpa(self, create_pdf_mock):
        "Accept terms post request with dpa acceptance."
        bob = self.bob
        bob.email = 'bob@external.com'
        bob.save()
        self.client.login(username='bob', password='password')

        response = self.client.post(
            '/account/profile/accept-terms/', {'accept_dpa_field': True}
        )

        self.assertRedirects(response, '/')
        self.assertMessages(
            response,
            [Message(level=25, message='You agreed to the required documents.')],
        )
        bob.refresh_from_db()
        self.assertIsNotNone(bob.dpa_accepted_at)
        create_pdf_mock.assert_called_once_with(bob.id)

    @override_settings(MMT_TERMS_VERSION=2)
    @mock.patch('mmt.my_account.views.create_dpa_pdf.delay')
    def test_accept_terms_post_dpa_and_terms(self, create_pdf_mock):
        "Accept terms post request with terms and dpa acceptance."
        bob = self.bob
        bob.email = 'bob@external.com'
        bob.save()
        self.client.login(username='bob', password='password')

        response = self.client.post(
            '/account/profile/accept-terms/',
            {'accept_terms_field': True, 'accept_dpa_field': True},
        )

        self.assertRedirects(response, '/')
        self.assertMessages(
            response,
            [Message(level=25, message='You agreed to the required documents.')],
        )
        bob.refresh_from_db()
        self.assertEqual(self.bob.terms_accepted_version, 2)
        self.assertIsNotNone(bob.dpa_accepted_at)
        create_pdf_mock.assert_called_once_with(bob.id)

    def test_accept_terms_logged_out(self):
        response = self.client.post(
            '/account/profile/accept-terms/', {'accept_terms_field': True}
        )
        self.assertRedirects(
            response, '/accounts/login/?next=/account/profile/accept-terms/'
        )

    # Leave this in, think about it later.
    @override_settings(MMT_TERMS_VERSION=2)
    def test_accept_terms_post_invalid(self):
        "Submitting without checking the required field re-renders the form."
        self.client.login(username='bob', password='password')

        response = self.client.post('/account/profile/accept-terms/', {})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(response.context['form'].is_valid())

    # Download DPA
    def test_download_dpa_success(self):
        "Returns the file with correct headers when DPA file exists."
        profile = self.bob.safe_profile
        fake_content = b'%PDF fake content'
        profile.dpa.save('dpa.pdf', ContentFile(fake_content))
        self.client.login(username='bob', password='password')

        response = self.client.get('/account/profile/dpa/')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['Content-Disposition'], 'inline; filename="dpa.pdf"')

        profile.dpa.delete()

    def test_download_dpa_logged_out(self):
        response = self.client.get('/account/profile/dpa/')
        self.assertRedirects(response, '/accounts/login/?next=/account/profile/dpa/')

    def test_download_dpa_no_file(self):
        "Returns 404 when no DPA is associated with the user."
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/dpa/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_download_dpa_file_missing_on_disk(self):
        "Returns 404 when dpa field is set but file does not exist on disk."
        profile = self.bob.safe_profile
        profile.dpa.name = 'uploads/dpas/missing.pdf'
        profile.save()
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/profile/dpa/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Debug page
    def test_debug_page_not_accessible(self):
        """Debug page is only accessible by superusers."""
        self.client.login(username='bob', password='password')
        response = self.client.get('/account/debug/')

        self.assertRedirects(response, '/')
