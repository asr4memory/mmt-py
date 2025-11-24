import TranscriptWord from './transcript_word';
import formatTimecode from '../helpers/format_timecode';

export default {
    components: {
        TranscriptWord,
    },
    name: 'TranscriptSegment',
    props: ['index', 'start', 'end', 'text', 'speaker', 'words'],
    data() {
        return {};
    },
    computed: {
        startTimecode() {
            return formatTimecode(this.start);
        },
        endTimecode() {
            return formatTimecode(this.end);
        },
    },
    template: `
    <div class="u-mt-small">
        <p>Segment {{index}}; Start: {{startTimecode}}, End: {{endTimecode}}</p>
        <p class="segment u-ll">
            <TranscriptWord word=" " :score="0" />
            <TranscriptWord v-for="(word, index) in words" :key="word.start"
                :index="index"
                :start="word.start" :end="word.end" :word="word.word"
                :speaker="word.speaker" :score="word.score" />
            <TranscriptWord word=" " :score="0" />
        </p>
    </div>
    `,
};
