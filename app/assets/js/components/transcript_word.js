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
        "dirty",
    ],
    data() {
        return {
            editMode: false,
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
            this.editMode = true;
            const span = event.target;
            this.$nextTick(() => {
                const input = span.firstElementChild;
                input.focus();
            });
        },
        handleInputBlur(event) {
            this.editMode = false;
            this.updateWord(this.segment_index, this.index, event.target.value);
        },
        handleEnterKey(event) {
            this.editMode = false;
            this.updateWord(this.segment_index, this.index, event.target.value);
            const input = event.target;
            const span = input.parentElement;
            const next = span.nextElementSibling;
            next?.focus();
        },
        handleKeyLeft(event) {
            const input = event.target;
            const span = input.parentElement;
            const prev = span.previousElementSibling;
            prev?.focus();
        },
        handleKeyRight(event) {
            const input = event.target;
            const span = input.parentElement;
            const next = span.nextElementSibling;
            next?.focus();
        }
    },
    template: `
    <span class="word"
        :class="{'word--dirty': dirty}"
        :tabindex="editMode ? -1 : 0"
        :style="{'background-color': backgroundColor }"
        @focus="handleFocus">
        {{word}}
        <input v-if="editMode" class="word__input"
            tabindex="0"
            :title="score"
            :value="word"
            @blur="handleInputBlur"
            @keyup.enter="handleEnterKey">
    </span>
    `,
};
