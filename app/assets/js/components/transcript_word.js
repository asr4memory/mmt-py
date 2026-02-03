import { mapActions } from "pinia";
import { useTranscriptStore } from "../transcript_store";
import formatTimecode from "../helpers/format_timecode";

export default {
    components: {},
    name: "TranscriptWord",
    props: [
        "segmentIndex",
        "index",
        "word",
    ],
    data() {
        return {
            editMode: false,
        };
    },
    computed: {
        backgroundColor() {
            return `hsl(208 71% 77% / ${this.word.score})`;
        },
        startTimecode() {
            return formatTimecode(this.word.start);
        },
        endTimecode() {
            return formatTimecode(this.word.end);
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateWord"]),
        handleFocus(event) {
            this.editMode = true;
            const span = event.target;
            this.$nextTick(() => {
                const input = span.firstElementChild;
                input?.focus();
            });
        },
        handleInputBlur(event) {
            this.editMode = false;
            this.updateWord(this.segmentIndex, this.index, event.target.value);
        },
        handleEnterKey(event) {
            const input = event.target;
            const span = input.parentElement;
            const next = span.nextElementSibling;
            if (next) {
                next.focus();
            } else {
                this.editMode = false;
                this.updateWord(this.segmentIndex, this.index, event.target.value);
            }
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
        },
        handleMouseOver() {
            this.$refs.popover.showPopover();
        },
        handleMouseOut() {
            this.$refs.popover.hidePopover();
        },
    },
    template: `
    <span class="word"
        :class="{'word--dirty': word.dirty}"
        :tabindex="editMode ? -1 : 0"
        :style="{'background-color': backgroundColor }"
        @mouseover="handleMouseOver"
        @mouseout="handleMouseOut"
        @focus="handleFocus">
        {{word.word}}
        <input v-if="editMode" class="word__input"
            tabindex="0"
            :value="word.word"
            @blur="handleInputBlur"
            @keyup.enter="handleEnterKey" />
        <div popover="hint" ref="popover" class="popover">
            <dl>
                <dt>Timecode</dt>
                <dd>{{startTimecode}}<br>{{endTimecode}}</dd>
                <dt>Score</dt>
                <dd>{{word.score}}</dd>
            </dl>
        </div>
    </span>
    `,
};
