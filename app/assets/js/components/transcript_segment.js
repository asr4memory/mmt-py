import TranscriptWord from "./transcript_word";
import formatTimecode from "../helpers/format_timecode";

export default {
    components: {
        TranscriptWord,
    },
    name: "TranscriptSegment",
    props: ["index", "segment"],
    computed: {
        startTimecode() {
            return formatTimecode(this.segment.start);
        },
        endTimecode() {
            return formatTimecode(this.segment.end);
        },
        isDirty() {
            return (this.segment.dirty === true)
                || (this.segment.words.some(word => word.dirty === true));
        },
    },
    template: `
    <div class="u-mt-small">
        <p>Segment {{index}}; Start: {{startTimecode}}, End: {{endTimecode}}</p>
        <p class="segment u-ll" :class="{'segment--dirty': isDirty}">
            <TranscriptWord v-for="(word, idx) in segment.words" :key="word.start"
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
