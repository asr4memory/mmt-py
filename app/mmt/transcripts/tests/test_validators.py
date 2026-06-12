import copy

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from mmt.transcripts.validators import validate_whisper_input

WHISPERX_CONTENT = {
    'language': 'en',
    'segments': [
        {
            'start': 0.46,
            'end': 1.54,
            'text': 'Yes, thank you.',
            'speaker': 'SPEAKER_00',
            'words': [
                {
                    'word': 'Yes,',
                    'start': 0.46,
                    'end': 0.58,
                    'speaker': 'SPEAKER_00',
                    'score': 0.996576,
                    'score_log': -0.010289878584444523,
                },
                {
                    'word': 'thank',
                    'start': 0.62,
                    'end': 0.82,
                    'speaker': 'SPEAKER_00',
                    'score': 0.991234,
                    'score_log': -0.043201837539672852,
                },
                {
                    'word': 'you.',
                    'start': 0.84,
                    'end': 0.96,
                    'speaker': 'SPEAKER_00',
                    'score': 0.998102,
                    'score_log': -0.005341018363833427,
                },
            ],
        }
    ],
    'word_segments': [{'word': 'Yes,', 'start': 0.46, 'end': 0.58}],
}

WHISPER_CONTENT = {
    'text': 'Hello world',
    'language': 'en',
    'segments': [
        {
            'id': 0,
            'seek': 0,
            'start': 0,
            'end': 1,
            'text': 'Hello world',
            'tokens': [50364, 2425, 1002, 50414],
            'temperature': 0.0,
            'avg_logprob': -0.27,
            'compression_ratio': 0.71,
            'no_speech_prob': 0.02,
            'words': [
                {'word': 'Hello', 'start': 0, 'end': 0.5, 'probability': 0.97},
                {'word': 'world', 'start': 0.5, 'end': 1, 'probability': 0.99},
            ],
        }
    ],
}


def make_content():
    """Return a fresh, valid transcript to mutate in tests."""
    return copy.deepcopy(WHISPERX_CONTENT)


class ValidateWhisperInputTests(SimpleTestCase):
    def test_valid_whisperx_content(self):
        """WhisperX output with speakers and scores passes."""
        validate_whisper_input(WHISPERX_CONTENT)

    def test_valid_whisper_content(self):
        """Plain Whisper output with word timestamps passes."""
        validate_whisper_input(WHISPER_CONTENT)

    def test_content_not_an_object(self):
        """Non-object JSON is rejected."""
        for content in ([], 'text', 42, None):
            with self.assertRaisesMessage(
                ValidationError, 'The transcript must be a JSON object.'
            ):
                validate_whisper_input(content)

    def test_segments_missing(self):
        """Content without segments is rejected."""
        with self.assertRaisesMessage(
            ValidationError, 'The transcript must contain a non-empty list of segments.'
        ):
            validate_whisper_input({})

    def test_segments_empty(self):
        """An empty segments list is rejected."""
        with self.assertRaisesMessage(
            ValidationError, 'The transcript must contain a non-empty list of segments.'
        ):
            validate_whisper_input({'segments': []})

    def test_segments_not_a_list(self):
        """A non-list segments value is rejected."""
        with self.assertRaisesMessage(
            ValidationError, 'The transcript must contain a non-empty list of segments.'
        ):
            validate_whisper_input({'segments': {}})

    def test_segment_not_an_object(self):
        """A non-object segment is rejected with its position."""
        content = make_content()
        content['segments'].append('not a segment')

        with self.assertRaisesMessage(
            ValidationError, 'Segment 2 must be a JSON object.'
        ):
            validate_whisper_input(content)

    def test_segment_without_timestamps(self):
        """A segment without numeric start/end is rejected."""
        content = make_content()
        del content['segments'][0]['start']

        with self.assertRaisesMessage(
            ValidationError, 'Segment 1 must have numeric start and end timestamps.'
        ):
            validate_whisper_input(content)

    def test_segment_with_boolean_timestamp(self):
        """Booleans do not count as numeric timestamps."""
        content = make_content()
        content['segments'][0]['end'] = True

        with self.assertRaisesMessage(
            ValidationError, 'Segment 1 must have numeric start and end timestamps.'
        ):
            validate_whisper_input(content)

    def test_segment_without_words(self):
        """A segment without a words list is rejected."""
        content = make_content()
        del content['segments'][0]['words']

        with self.assertRaisesMessage(
            ValidationError, 'Segment 1 must contain a non-empty list of words.'
        ):
            validate_whisper_input(content)

    def test_segment_with_empty_words(self):
        """A segment with an empty words list is rejected."""
        content = make_content()
        content['segments'][0]['words'] = []

        with self.assertRaisesMessage(
            ValidationError, 'Segment 1 must contain a non-empty list of words.'
        ):
            validate_whisper_input(content)

    def test_word_not_an_object(self):
        """A non-object word is rejected with its position."""
        content = make_content()
        content['segments'][0]['words'][1] = 'thank'

        with self.assertRaisesMessage(
            ValidationError, 'Word 2 in segment 1 must be a JSON object.'
        ):
            validate_whisper_input(content)

    def test_word_without_text(self):
        """A word without text is rejected."""
        content = make_content()
        del content['segments'][0]['words'][2]['word']

        with self.assertRaisesMessage(
            ValidationError, 'Word 3 in segment 1 must have text.'
        ):
            validate_whisper_input(content)

    def test_word_with_blank_text(self):
        """A word with whitespace-only text is rejected."""
        content = make_content()
        content['segments'][0]['words'][0]['word'] = '  '

        with self.assertRaisesMessage(
            ValidationError, 'Word 1 in segment 1 must have text.'
        ):
            validate_whisper_input(content)

    def test_word_without_timestamps(self):
        """A word without start/end is rejected."""
        content = make_content()
        del content['segments'][0]['words'][1]['start']

        with self.assertRaisesMessage(
            ValidationError,
            'Word 2 in segment 1 must have numeric start and end timestamps. '
            'Word-timestamped Whisper/WhisperX output is required.',
        ):
            validate_whisper_input(content)

    def test_word_with_non_numeric_timestamp(self):
        """A word with a string timestamp is rejected."""
        content = make_content()
        content['segments'][0]['words'][0]['end'] = '0.58'

        with self.assertRaisesMessage(
            ValidationError,
            'Word 1 in segment 1 must have numeric start and end timestamps. '
            'Word-timestamped Whisper/WhisperX output is required.',
        ):
            validate_whisper_input(content)

    def test_word_with_boolean_timestamp(self):
        """Booleans do not count as numeric word timestamps."""
        content = make_content()
        content['segments'][0]['words'][0]['start'] = False

        with self.assertRaisesMessage(
            ValidationError,
            'Word 1 in segment 1 must have numeric start and end timestamps. '
            'Word-timestamped Whisper/WhisperX output is required.',
        ):
            validate_whisper_input(content)

    def test_word_starting_after_it_ends(self):
        """A word whose start is after its end is rejected."""
        content = make_content()
        content['segments'][0]['words'][0]['start'] = 0.6
        content['segments'][0]['words'][0]['end'] = 0.46

        with self.assertRaisesMessage(
            ValidationError, 'Word 1 in segment 1 must not start after it ends.'
        ):
            validate_whisper_input(content)
