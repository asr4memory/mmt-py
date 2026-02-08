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
    methods: {
        play() {
            const player = document.getElementById('media-player');
            if (player) {
                player.currentTime = this.segment.start;
                player.play();
            }
        },
    },
    template: `
    <div class="u-mb-small">
        <p>
            Segment {{index}};
            <button type="button" @click="play">Start: {{startTimecode}}</button>
            End: {{endTimecode}}
        </p>
        <p class="segment u-ll" :class="{'segment--dirty': isDirty}">
            <TranscriptWord v-for="(word, idx) in segment.words" :key="word.start"
                :segmentIndex="index"
                :index="idx"
                :word="word" />
        </p>
    </div>
    `,
};
