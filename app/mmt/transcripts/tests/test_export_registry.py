"""Tests for the exporter registry and the timecode helper.

The registry is what the view resolves a URL segment against and what the
detail page renders its list from, so its invariants are tested once here
rather than in every format's test.
"""

import re

from mmt.transcripts.exporters import EXPORT_FORMATS
from mmt.transcripts.exporters.timecode import hhmmssmmm

# The display order pinned in specs/2026-07-30-transcript-export.md: the
# machine-readable full-fidelity format first, then the segment formats, then
# the format meant for reading. Formats not yet implemented are absent from the
# registry, which is why the assertion below filters rather than compares.
PINNED_ORDER = ['whisperx', 'vtt', 'srt', 'csv', 'tei', 'pdf']


def test_keys_match_their_dictionary_key():
    for key, export_format in EXPORT_FORMATS.items():
        assert export_format.key == key


def test_keys_are_url_safe():
    for key in EXPORT_FORMATS:
        assert re.fullmatch(r'[a-z0-9-]+', key)


def test_every_format_has_an_extension_and_a_content_type():
    for export_format in EXPORT_FORMATS.values():
        assert export_format.extension
        assert not export_format.extension.startswith('.')
        assert export_format.content_type


def test_every_format_has_a_name_and_a_description():
    for export_format in EXPORT_FORMATS.values():
        assert str(export_format.name)
        assert str(export_format.description)


def test_every_format_is_registered_in_the_pinned_order():
    assert list(EXPORT_FORMATS) == [
        key for key in PINNED_ORDER if key in EXPORT_FORMATS
    ]


def test_whisperx_is_registered():
    assert EXPORT_FORMATS['whisperx'].extension == 'json'
    assert EXPORT_FORMATS['whisperx'].content_type == 'application/json'


def test_csv_is_registered():
    assert EXPORT_FORMATS['csv'].extension == 'csv'
    assert EXPORT_FORMATS['csv'].content_type == 'text/csv; charset=utf-8'


def test_tei_is_registered():
    assert EXPORT_FORMATS['tei'].extension == 'xml'
    assert EXPORT_FORMATS['tei'].content_type == 'application/tei+xml; charset=utf-8'


def test_hhmmssmmm_formats_zero():
    assert hhmmssmmm(0.0) == '00:00:00.000'


def test_hhmmssmmm_pads_every_component():
    assert hhmmssmmm(4.2) == '00:00:04.200'
    assert hhmmssmmm(65.07) == '00:01:05.070'
    assert hhmmssmmm(3723.008) == '01:02:03.008'


def test_hhmmssmmm_truncates_rather_than_rounds():
    """A rounded end time can fall after the next cue's start."""
    assert hhmmssmmm(1.9999) == '00:00:01.999'
    assert hhmmssmmm(12.3456) == '00:00:12.345'


def test_hhmmssmmm_is_not_disturbed_by_binary_floating_point():
    """0.3 * 1000 is 299.99999999999994, which must not truncate to 299."""
    assert hhmmssmmm(0.3) == '00:00:00.300'
    assert hhmmssmmm(4.7) == '00:00:04.700'


def test_hhmmssmmm_does_not_wrap_hours_at_24():
    assert hhmmssmmm(90061.5) == '25:01:01.500'


def test_hhmmssmmm_uses_the_given_millisecond_separator():
    assert hhmmssmmm(4.2, millisecond_separator=',') == '00:00:04,200'
