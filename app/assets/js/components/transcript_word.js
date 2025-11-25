import { mapState, mapWritableState, mapActions } from "pinia";
import { useTranscriptStore } from "../transcript_store";

export default {
    components: {},
    name: "TranscriptWord",
    props: [
        "segment_index",
        "index",
        "start",
        "end",
        "word",
        "speaker",
        "score",
    ],
    data() {
        return {
        };
    },
    computed: {
        backgroundColor() {
            return `hsl(208 71% 77% / ${this.score})`;
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateWord"]),
        handleInputChange(event) {
            //this.updateWord(this.segment_index, this.index, event.target.innerText);
        },
        handleFocus(event) {
        },
        handleBlur(event) {
            this.updateWord(this.segment_index, this.index, event.target.value);
        },
        handleKeyRight(event) {
            console.log(event);
        }
    },
    template: `
    <input class="word"
        @input="handleInputChange"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown.right="handleKeyRight"
        contenteditable="plaintext-only"
        tabindex="0"
        :style="{'background-color': backgroundColor }"
        :title="score"
        :value="word">
    `,
};
