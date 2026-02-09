import TranscriptWord from "./transcript_word";
import formatTimecode from "../helpers/format_timecode";

export default {
    components: {
        TranscriptWord,
    },
    name: "TranscriptSegment",
    props: ["index", "segment"],
    computed: {
        formattedID() {
            return String(this.index).padStart(3, "0");
        },
        startTimecode() {
            return formatTimecode(this.segment.start);
        },
        endTimecode() {
            return formatTimecode(this.segment.end);
        },
        isDirty() {
            return (
                this.segment.dirty === true ||
                this.segment.words.some((word) => word.dirty === true)
            );
        },
    },
    methods: {
        play() {
            const player = document.getElementById("media-player");
            if (player) {
                player.currentTime = this.segment.start;
                player.play();
            }
        },
    },
    template: `
    <div class="segment u-mb-small">
        <header class="segment__header">
            <span class="segment__id">#{{formattedID}}</span>
            <button class="segment__timecode" type="button"
                @click="play">{{startTimecode}}–{{endTimecode}}</button>
            <span class="segment__extra">{{segment.speaker}}</span>
        </header>
        <p class="segment__text u-ll" :class="{'segment__text--dirty': isDirty}">
            <TranscriptWord v-for="(word, idx) in segment.words" :key="word.start"
                :segmentIndex="index"
                :index="idx"
                :word="word" />
        </p>
    </div>
    `,
};
