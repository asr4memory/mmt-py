from uuid import uuid4

from .mmt_schema import Transcript, validate_mmt_content

# Single source of truth for speaker colours (currently mirrored in the Vue
# store's SPEAKER_COLORS). Once content is born enriched, the frontend should
# read colours from the file instead of re-deriving them.
SPEAKER_COLORS = ['#5b9bd5', '#70ad47', '#ed7d31', '#9b59b6', '#17a589']


def _new_id(prefix: str) -> str:
    return f'{prefix}_{uuid4().hex}'


def normalize_content(content: dict) -> Transcript:
    """Bring stored content up to the current mmt-transcript version.

    Version-aware and idempotent: content that is already mmt-transcript is
    re-validated and returned unchanged (ids are preserved); legacy Whisper
    input (no format/version) is upgraded. Assumes Whisper input has already
    passed validate_whisper_input().

    Args:
        content: Either lenient Whisper/whisperX output (a dict with a
            ``segments`` list) or an already-normalized mmt-transcript dict.

    Returns:
        A validated ``Transcript`` model. Persist it as JSON with
        ``.model_dump()``.
    """
    if content.get('format') == 'mmt-transcript':
        return validate_mmt_content(content)

    return _whisper_to_mmt(content)


def apply_mention_spans(content: dict, results: list[list[dict]]) -> dict:
    """Materialise the NER service's word-index spans into mentions.

    ``results`` is the ``/extract`` response: one span list per segment
    (parallel to ``content['segments']``), each span a half-open
    ``{start, end, label, score}`` over that segment's word indices, with
    spans within a segment guaranteed non-overlapping by the service. Each
    span becomes one entry in the transcript-level ``mentions`` map, and the
    covered words point at it via ``mentionId``. Pre-existing mentions and
    word links are replaced. Mutates and returns ``content``.
    """
    mentions = {}
    for segment, spans in zip(content['segments'], results, strict=True):
        for word in segment['words']:
            word['mentionId'] = None
        for span in spans:
            mention_id = _new_id('men')
            mentions[mention_id] = {'label': span['label'], 'score': span['score']}
            for index in range(span['start'], span['end']):
                segment['words'][index]['mentionId'] = mention_id
    content['mentions'] = mentions
    return content


def _whisper_to_mmt(whisper: dict) -> Transcript:
    # Distinct, non-empty speaker names from segments and words, sorted so the
    # colour assignment is stable (mirrors the frontend get_all_speakers).
    names = sorted(
        {
            name
            for segment in whisper['segments']
            for raw in [
                segment.get('speaker'),
                *(word.get('speaker') for word in segment['words']),
            ]
            if (name := (raw or '').strip())
        }
    )
    speakers = [
        {
            'id': _new_id('spk'),
            'name': name,
            'color': SPEAKER_COLORS[index % len(SPEAKER_COLORS)],
        }
        for index, name in enumerate(names)
    ]
    name_to_id = {speaker['name']: speaker['id'] for speaker in speakers}

    def speaker_id(raw):
        return name_to_id.get((raw or '').strip())

    segments = []
    for segment in whisper['segments']:
        segment_speaker = speaker_id(segment.get('speaker'))
        segments.append(
            {
                'id': _new_id('seg'),
                'start': segment['start'],
                'end': segment['end'],
                'text': segment.get('text', ''),
                'speakerId': segment_speaker,
                'words': [
                    {
                        'id': _new_id('wrd'),
                        'start': word['start'],
                        'end': word['end'],
                        'word': word['word'],
                        # Whisper-plain words carry no score; whisperX does.
                        'score': word.get('score', 1.0),
                        # Words inherit the segment speaker when unlabelled.
                        'speakerId': speaker_id(word.get('speaker')) or segment_speaker,
                        # Linked to a mention later by the NER service.
                        'mentionId': None,
                    }
                    for word in segment['words']
                ],
            }
        )

    result = {
        'format': 'mmt-transcript',
        'version': 1,
        'speakers': speakers,
        'segments': segments,
    }
    # The oracle: the transform is correct iff its output conforms.
    return validate_mmt_content(result)
