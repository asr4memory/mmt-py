from datetime import UTC, datetime
from unittest import mock

from django.test import TestCase

from mmt.my_account.pdf import generate_dpa_pdf


class GenerateDpaPdfTests(TestCase):
    @mock.patch('weasyprint.HTML')
    def test_generate_dpa_pdf(self, html_mock):
        html_mock.return_value.write_pdf.return_value = b'%PDF'

        result = generate_dpa_pdf(
            'Bob Smith', datetime(2026, 5, 7, 8, 0, 0, tzinfo=UTC)
        )

        self.assertEqual(result, b'%PDF')
        rendered = html_mock.call_args.kwargs['string']
        self.assertIn('Bob Smith', rendered)
        self.assertIn('07.05.2026', rendered)
        self.assertIn('Vertrag zur Auftragsverarbeitung gemäß Art. 28 DSGVO', rendered)
