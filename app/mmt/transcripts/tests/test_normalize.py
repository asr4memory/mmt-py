from mmt.transcripts.mmt_schema import validate_mmt_content
from mmt.transcripts.normalize import normalize_content


def whisper_input():
    return {
        'segments': [
            {
                'start': 14,
                'end': 20.5,
                'text': 'My transcript is fine.',
                'speaker': 'SPEAKER_01',
                'words': [
                    {
                        'start': 14,
                        'end': 14.5,
                        'word': 'My',
                        'speaker': 'SPEAKER_01',
                        'score': 0.5,
                    },
                    {
                        'start': 15,
                        'end': 17,
                        'word': 'transcript',
                        # no score, no speaker
                    },
                ],
            }
        ]
    }


def test_adds_format_and_version():
    result = normalize_content(whisper_input())
    assert result.format == 'mmt-transcript'
    assert result.version == 1


def test_returns_validated_transcript():
    # normalize_content returns a Transcript that re-dumps to conforming content.
    result = normalize_content(whisper_input())
    validate_mmt_content(result.model_dump())


def test_mints_unique_prefixed_ids():
    result = normalize_content(whisper_input())
    segment = result.segments[0]
    ids = [segment.id, *(w.id for w in segment.words)]
    assert segment.id.startswith('seg_')
    assert all(w.id.startswith('wrd_') for w in segment.words)
    assert all(s.id.startswith('spk_') for s in result.speakers)
    assert len(set(ids)) == len(ids)


def test_builds_speakers_and_maps_refs():
    result = normalize_content(whisper_input())
    assert [s.name for s in result.speakers] == ['SPEAKER_01']
    speaker = result.speakers[0]
    assert speaker.color == '#5b9bd5'
    assert result.segments[0].speakerId == speaker.id
    assert result.segments[0].words[0].speakerId == speaker.id


def test_word_inherits_segment_speaker_when_unlabelled():
    result = normalize_content(whisper_input())
    speaker = result.speakers[0]
    # Second word had no speaker; it inherits the segment's.
    assert result.segments[0].words[1].speakerId == speaker.id


def test_defaults_missing_word_score():
    result = normalize_content(whisper_input())
    assert result.segments[0].words[1].score == 1.0


def test_empty_speaker_becomes_no_speaker():
    content = whisper_input()
    content['segments'][0]['speaker'] = ''
    for word in content['segments'][0]['words']:
        word['speaker'] = '   '
    result = normalize_content(content)
    assert result.speakers == []
    assert result.segments[0].speakerId is None
    assert all(w.speakerId is None for w in result.segments[0].words)


def test_collects_speaker_from_words_only():
    content = whisper_input()
    del content['segments'][0]['speaker']
    content['segments'][0]['words'][0]['speaker'] = 'Bob'
    result = normalize_content(content)
    assert [s.name for s in result.speakers] == ['Bob']


def test_distinct_speakers_sorted_and_coloured():
    content = whisper_input()
    content['segments'][0]['speaker'] = 'Zoe'
    content['segments'][0]['words'][0]['speaker'] = 'Zoe'
    content['segments'][0]['words'][1]['speaker'] = 'Amy'
    result = normalize_content(content)
    assert [s.name for s in result.speakers] == ['Amy', 'Zoe']
    assert [s.color for s in result.speakers] == ['#5b9bd5', '#70ad47']


def test_drops_unknown_whisper_keys():
    content = whisper_input()
    content['word_segments'] = [{'anything': True}]
    content['language'] = 'en'
    result = normalize_content(content)  # would fail validation if kept
    dumped = result.model_dump()
    assert 'word_segments' not in dumped
    assert 'language' not in dumped


def test_idempotent_on_already_normalized():
    once = normalize_content(whisper_input())
    twice = normalize_content(once.model_dump())
    assert [s.id for s in twice.speakers] == [s.id for s in once.speakers]
    assert twice.segments[0].id == once.segments[0].id
    assert twice.segments[0].words[0].id == once.segments[0].words[0].id
