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


def extract_mentions(content: dict) -> dict:
    """Materialise the NER service's flat per-word signal into mentions.

    The NER service tags words with ``ner_entity`` and, for the words of one
    multi-word entity, a shared (segment-scoped) ``word_group_index``. This
    collapses that signal into the canonical model: a transcript-level
    ``mentions`` list, with each tagged word pointing at its mention via
    ``ner_mention_id``. The flat fields are dropped. Mutates and returns
    ``content``.
    """
    mentions = []
    for segment in content['segments']:
        group_to_mention = {}
        for word in segment['words']:
            label = word.pop('ner_entity', None)
            group = word.pop('word_group_index', None)
            if label is None:
                word['ner_mention_id'] = None
                continue
            mention_id = group_to_mention.get(group) if group is not None else None
            if mention_id is None:
                mention_id = _new_id('men')
                mentions.append({'id': mention_id, 'label': label})
                if group is not None:
                    group_to_mention[group] = mention_id
            word['ner_mention_id'] = mention_id
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
                        'ner_mention_id': None,
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
