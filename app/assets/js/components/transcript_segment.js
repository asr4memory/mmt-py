import TranscriptWord from './transcript_word';

export default {
    components: {
        TranscriptWord,
    },
    name: 'TranscriptSegment',
    props: ['index', 'start', 'end', 'text', 'speaker', 'words'],
    data() {
        return {};
    },
    template: `
    <div class="u-mt-small">
        <p>Segment {{index}}; Start: {{start}}, End: {{end}}</p>
        <p class="segment">
            <TranscriptWord v-for="(word, index) in words" :key="word.start"
                :index="index"
                :start="word.start" :end="word.end" :word="word.word"
                :speaker="word.speaker" :score="word.score" />
        </p>
    </div>
    `,
};
