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
        showEntities: Boolean,
        showEdits: Boolean,
    },
    data() {
        return {
            editMode: false,
        };
    },
    beforeUnmount() {
        window.removeEventListener("scroll", this.handleScroll, {
            capture: true,
        });
    },
    computed: {
        backgroundColor() {
            return `hsl(208 71% 77% / ${1 - this.word.score})`;
        },
        anchorName() {
            // Must be unique per word: the popover is in the top layer,
            // where a name shared by all words would resolve to the last
            // word in the document.
            return `--word-${this.segmentIndex}-${this.index}`;
        },
        wordStyle() {
            const style = { "anchor-name": this.anchorName };
            if (this.showConfidence) {
                style["background-color"] = this.backgroundColor;
            }
            return style;
        },
        startTimecode() {
            return formatTimecode(this.word.start);
        },
        endTimecode() {
            return formatTimecode(this.word.end);
        },
        formattedScore() {
            // Word confidence score.
            return this.word.score.toLocaleString(
                document.documentElement.lang,
            );
        },
        entityClass() {
            if (this.word.ner_entity) {
                switch (this.word.ner_entity) {
                    case "ORG":
                        return "word--org";
                    case "PER":
                        return "word--per";
                    case "DATE":
                        return "word--date";
                    case "LOC":
                        return "word--loc";
                }
            } else {
                return "";
            }
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, [
            "updateWord",
            "insertLeft",
            "insertRight",
            "deleteWord",
        ]),
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
            const popover = this.$refs.popover;
            if (popover && !popover.matches(":popover-open")) {
                popover.showPopover({ source: this.$refs.word });
                this.positionPopoverFallback();
                // Anchored popovers do not reliably track their anchor
                // across scrolls (mouse wheel, auto-scroll during
                // playback), so hide on the first scroll instead.
                window.addEventListener("scroll", this.handleScroll, {
                    capture: true,
                    passive: true,
                });
            }
        },
        positionPopoverFallback() {
            // Browsers without CSS anchor positioning render the popover
            // at its static position (the line below the word), so place
            // it next to the word manually.
            if (
                CSS.supports("position-anchor", "--word") &&
                CSS.supports("position-area", "bottom")
            ) {
                return;
            }
            const popover = this.$refs.popover;
            const wordRect = this.$refs.word.getBoundingClientRect();
            const popoverRect = popover.getBoundingClientRect();
            let top = wordRect.bottom;
            if (top + popoverRect.height > window.innerHeight) {
                top = wordRect.top - popoverRect.height;
            }
            let left =
                wordRect.left + (wordRect.width - popoverRect.width) / 2;
            left = Math.max(
                0,
                Math.min(left, window.innerWidth - popoverRect.width),
            );
            popover.style.top = `${top}px`;
            popover.style.left = `${left}px`;
        },
        handleMouseOut() {
            this.hidePopover();
        },
        handleScroll() {
            this.hidePopover();
        },
        hidePopover() {
            const popover = this.$refs.popover;
            if (popover?.matches(":popover-open")) {
                popover.hidePopover();
            }
            window.removeEventListener("scroll", this.handleScroll, {
                capture: true,
            });
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
        :class="[{'word--dirty': word.dirty && showEdits}, showEntities ? entityClass : '']"
        :tabindex="editMode ? -1 : 0"
        :style="wordStyle"
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
        <div v-if="!editMode" popover="hint" ref="popover" class="popover"
            :style="{'position-anchor': anchorName}">
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
