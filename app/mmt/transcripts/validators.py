from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def _is_timestamp(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_whisper_input(content):
    """Check that content is word-timestamped Whisper/whisperX output.

    Lenient input-side validation (see docs/mmt-transcript-format.md): only
    the structure the editor depends on is enforced; extra keys like
    speaker, score or word_segments are ignored. Fails fast on the first
    problem with a 1-based position in the message.
    """
    if not isinstance(content, dict):
        raise ValidationError(_('The transcript must be a JSON object.'))

    segments = content.get('segments')
    if not isinstance(segments, list) or not segments:
        raise ValidationError(
            _('The transcript must contain a non-empty list of segments.')
        )

    for segment_index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            raise ValidationError(
                _('Segment %(segment)s must be a JSON object.'),
                params={'segment': segment_index},
            )

        if not _is_timestamp(segment.get('start')) or not _is_timestamp(
            segment.get('end')
        ):
            raise ValidationError(
                _('Segment %(segment)s must have numeric start and end timestamps.'),
                params={'segment': segment_index},
            )

        words = segment.get('words')
        if not isinstance(words, list) or not words:
            raise ValidationError(
                _('Segment %(segment)s must contain a non-empty list of words.'),
                params={'segment': segment_index},
            )

        for word_index, word in enumerate(words, start=1):
            params = {'word': word_index, 'segment': segment_index}

            if not isinstance(word, dict):
                raise ValidationError(
                    _('Word %(word)s in segment %(segment)s must be a JSON object.'),
                    params=params,
                )

            text = word.get('word')
            if not isinstance(text, str) or not text.strip():
                raise ValidationError(
                    _('Word %(word)s in segment %(segment)s must have text.'),
                    params=params,
                )

            if not _is_timestamp(word.get('start')) or not _is_timestamp(
                word.get('end')
            ):
                raise ValidationError(
                    _(
                        'Word %(word)s in segment %(segment)s must have numeric '
                        'start and end timestamps. Word-timestamped '
                        'Whisper/WhisperX output is required.'
                    ),
                    params=params,
                )

            if word['start'] > word['end']:
                raise ValidationError(
                    _(
                        'Word %(word)s in segment %(segment)s must not start after it ends.'
                    ),
                    params=params,
                )
