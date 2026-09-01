import pytest

from mmt.uploaded_files.filenames import fit_filename, storage_filename

# fit_filename: NAME_MAX is 255 bytes on Linux, and the stored name is a path
# component that later grows by a duplicate suffix and by ".mp4" for the web
# version, so the limit is on bytes and leaves headroom below 255.


def test_fit_filename_leaves_a_short_name_alone():
    assert fit_filename('interview.mp4') == 'interview.mp4'


def test_fit_filename_truncates_the_stem_and_keeps_the_extension():
    name = f'{"a" * 300}.mp4'

    result = fit_filename(name)

    assert result.endswith('.mp4')
    assert len(result.encode('utf-8')) == 200


def test_fit_filename_counts_bytes_not_characters():
    """Each umlaut is two bytes in UTF-8, so 150 of them exceed the limit."""
    name = f'{"ä" * 150}.mp4'

    result = fit_filename(name)

    assert len(result.encode('utf-8')) <= 200
    assert len(result) < len(name)


def test_fit_filename_does_not_cut_a_character_in_half():
    # The budget for the stem is an odd number of bytes, so a naive slice ends
    # inside a two-byte character.
    result = fit_filename(f'{"ä" * 150}.mp3', limit=101)

    assert result == f'{"ä" * 48}.mp3'


def test_fit_filename_keeps_a_name_without_an_extension():
    result = fit_filename('a' * 300)

    assert result == 'a' * 200


def test_fit_filename_splits_at_the_last_dot():
    result = fit_filename(f'{"a" * 300}.tar.gz')

    assert result.endswith('.gz')
    assert len(result.encode('utf-8')) == 200


def test_fit_filename_keeps_a_dotfile_whole():
    """A leading dot starts the name, it does not start an extension."""
    result = fit_filename(f'.{"a" * 300}', limit=10)

    assert result == '.aaaaaaaaa'


def test_fit_filename_cuts_a_name_that_is_one_long_extension():
    """There is no stem to shorten, so the whole name is cut to the limit."""
    result = fit_filename(f'a.{"b" * 300}', limit=10)

    assert result == 'a.bbbbbbbb'


# storage_filename: the stored name is a path component an administrator reads
# in a directory listing and types into a shell, so it is transliterated to
# ASCII. The submitted name is kept in UploadedFile.original_filename.


@pytest.mark.parametrize(
    'submitted,stored',
    [
        ('rita fernández 2', 'rita_fernandez_2'),
        ('Ana González nur audio', 'ana_gonzalez_nur_audio'),
        ('Ölbäume Übersicht.mp4', 'olbaume_ubersicht.mp4'),
        ('Straße.mp4', 'strasse.mp4'),
        ('Łódź.mp4', 'lodz.mp4'),
        ('ﬁle.mp4', 'file.mp4'),
        ('Interview.MP4', 'interview.mp4'),
        ('-i tricky.mp4', 'i_tricky.mp4'),
        ('.htaccess', 'htaccess'),
        ('რთ.mp4', 'rt.mp4'),
        ('interview რთ.mp4', 'interview_rt.mp4'),
        ('Интервью.mp4', 'intervyu.mp4'),
        ('日本語.mp3', 'ribenyu.mp3'),
        ('Ελλάδα.mp4', 'ellada.mp4'),
        ('😀.mp4', 'grinning.mp4'),
        ('...', 'file'),
    ],
)
def test_storage_filename_examples(submitted, stored):
    assert storage_filename(submitted) == stored


def test_storage_filename_collapses_runs_of_underscores():
    assert storage_filename('a   b ~ c.mp4') == 'a_b_c.mp4'


def test_storage_filename_strips_separators_from_both_ends_of_the_stem():
    assert storage_filename('__interview--.mp4') == 'interview.mp4'


def test_storage_filename_falls_back_when_the_stem_is_empty():
    """A name made only of characters outside the set leaves no stem."""
    assert storage_filename('!?.mp4') == 'file.mp4'


def test_storage_filename_applies_the_byte_limit_after_transliteration():
    """A romanisation can be longer than the name it came from."""
    result = storage_filename(f'{"ß" * 150}.mp4')

    assert result == f'{"ss" * 98}.mp4'
    assert len(result.encode('utf-8')) == 200
