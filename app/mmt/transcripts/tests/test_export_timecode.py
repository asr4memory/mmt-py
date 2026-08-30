from mmt.transcripts.exporters.timecode import hhmmssmmm


def test_zero_is_written_with_every_field_present():
    assert hhmmssmmm(0.0) == '00:00:00.000'


def test_every_field_is_padded_to_its_width():
    assert hhmmssmmm(3661.007) == '01:01:01.007'


def test_milliseconds_are_truncated_and_not_rounded():
    assert hhmmssmmm(1.9999) == '00:00:01.999'


def test_hours_are_not_truncated_at_24():
    # 25 hours and one second.
    assert hhmmssmmm(90001.0) == '25:00:01.000'


def test_the_millisecond_separator_can_be_a_comma():
    assert hhmmssmmm(4.2, millisecond_separator=',') == '00:00:04,200'
