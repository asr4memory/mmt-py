from mmt.core.templatetags.core_extras import category_label


def test_category_label():
    assert category_label('video/mp4') == 'Video'
    assert category_label('audio/mpeg') == 'Audio'
    assert category_label('application/pdf') == 'PDF'
    assert category_label('image/png') == 'Image'
    assert category_label('text/plain') == 'Text'
    assert category_label('application/zip') == 'Other'
