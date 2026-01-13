import TranscriptWord from "./transcript_word";
import formatTimecode from "../helpers/format_timecode";

export default {
    components: {
        TranscriptWord,
    },
    name: "TranscriptSegment",
    props: ["index", "start", "end", "text", "speaker", "words"],
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
        dirty() {
            return this.words.some(word => word.dirty);
        },
    },
    template: `
    <div class="u-mt-small">
        <p>Segment {{index}}; Start: {{startTimecode}}, End: {{endTimecode}}</p>
        <p class="segment u-ll" :class="{'segment--dirty': dirty}">
            <TranscriptWord v-for="(word, idx) in words" :key="word.start"
                :segment_index="index"
                :index="idx"
                :start="word.start"
                :end="word.end"
                :word="word.word"
                :speaker="word.speaker"
                :score="word.score"
                :dirty="word.dirty" />
        </p>
    </div>
    `,
};
