import { mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import TimeCode from "./time_code";
import formatTimecode from "../helpers/format_timecode";
import seekAndPlay from "../helpers/seek_and_play";

export default {
    components: { TimeCode },
    name: "TranscriptWord",
    props: {
        segmentIndex: Number,
        index: Number,
        word: Object,
        showConfidence: Boolean,
    },
    data() {
        return {
            editMode: false,
        };
    },
    computed: {
        backgroundColor() {
            return `hsl(208 71% 77% / ${1 - this.word.score})`;
        },
        startTimecode() {
            return formatTimecode(this.word.start);
        },
        endTimecode() {
            return formatTimecode(this.word.end);
        },
        formattedScore() {
            // Word confidence score.
            return this.word.score.toLocaleString();
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, ["updateWord", "insertLeft", "insertRight", "deleteWord"]),
        handleFocus(event) {
            this.editMode = true;
            const span = event.target;
            this.$nextTick(() => {
                const input = span.firstElementChild;
                input?.focus();
            });
        },
        handleInputBlur(event) {
            this.updateWord(this.segmentIndex, this.index, event.target.value);
            this.$nextTick(() => {
                this.editMode = false;
            });
        },
        handleEnterKey(event) {
            const input = event.target;
            const span = input.parentElement;
            const next = span.nextElementSibling;
            if (next) {
                next.focus();
            } else {
                this.editMode = false;
                this.updateWord(
                    this.segmentIndex,
                    this.index,
                    event.target.value,
                );
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
            if (this.$refs.popover) {
                this.$refs.popover.showPopover({ source: this.$refs.word });
            }
        },
        handleMouseOut() {
            if (this.$refs.popover) {
                this.$refs.popover.hidePopover();
            }
        },
        play() {
            const player = document.getElementById("media-player");
            if (player) {
                seekAndPlay(player, this.word.start);
            }
        },
        handleLeftInsert(event) {
            this.insertLeft(this.segmentIndex, this.index);
        },
        handleRightInsert(event) {
            this.insertRight(this.segmentIndex, this.index);
        },
        handleRemove(event) {
            this.deleteWord(this.segmentIndex, this.index);
        },
    },
    template: `
    <span class="word"
        :class="{'word--dirty': word.dirty}"
        :tabindex="editMode ? -1 : 0"
        :style="showConfidence ? {'background-color': backgroundColor } : null"
        ref="word"
        @mouseover="handleMouseOver"
        @mouseout="handleMouseOut"
        @focus="handleFocus"
        @click.shift="play">
        {{word.word}}
        <input v-if="editMode" class="word__input"
            tabindex="0"
            :value="word.word"
            @blur="handleInputBlur"
            @click.shift="play"
            @keyup.enter="handleEnterKey" />
        <div v-if="!editMode" popover="hint" ref="popover" class="popover">
            <header class="popover__header">
                <button type="button" :title="$t('add_word_left')"
                    @click="handleLeftInsert">+</button>
                <button type="button" :title="$t('remove_word')"
                    @click="handleRemove">&times;</button>
                <button type="button" :title="$t('add_word_right')"
                    @click="handleRightInsert">+</button>
            </header>
            <hr>
            <TimeCode :seconds="word.start"/>–<TimeCode :seconds="word.end"/><br>
            {{word.speaker}}<br v-if="word.speaker">
            {{$t('score')}} {{formattedScore}}
        </div>
    </span>
    `,
};
