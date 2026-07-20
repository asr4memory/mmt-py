from mmt.core.templatetags.core_extras import file_category_label


def test_file_category_label_known_values():
    assert file_category_label('video') == 'Video'
    assert file_category_label('audio') == 'Audio'
    assert file_category_label('pdf') == 'PDF'
    assert file_category_label('image') == 'Image'
    assert file_category_label('text') == 'Text'


def test_file_category_label_falls_back_to_value():
    assert file_category_label('application/zip') == 'application/zip'
