import { mapState, mapWritableState, mapActions } from "pinia";

import { useTranscriptStore } from "../transcript_store";
import TimecodeInput from "./timecode_input";
import TranscriptWord from "./transcript_word";
import formatTimecode from "../helpers/format_timecode";
import seekAndPlay from "../helpers/seek_and_play";

export default {
    components: {
        TimecodeInput,
        TranscriptWord,
    },
    name: "TranscriptSegment",
    props: {
        index: Number,
        segment: Object,
        currentTime: Number,
        active: Boolean,
        showConfidence: Boolean,
        autoScroll: Boolean,
    },
    emits: ["activate-segment"],
    computed: {
        formattedID() {
            return String(this.segment.id).padStart(3, "0");
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
        isCurrent() {
            return (
                this.segment.start <= this.currentTime &&
                this.currentTime <= this.segment.end
            );
        },
    },
    watch: {
        isCurrent(newValue, oldValue) {
            if (this.autoScroll && newValue === true) {
                this.$refs.container.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                });
            }
        },
    },
    methods: {
        ...mapActions(useTranscriptStore, [
            "insertSegmentBefore",
            "deleteSegment",
        ]),
        play() {
            const player = document.getElementById("media-player");
            if (player) {
                seekAndPlay(player, this.segment.start);
            }
        },
        insert() {
            this.insertSegmentBefore("newSegment", this.segment.id);
        },
        remove() {
            this.deleteSegment(this.segment.id);
        },
        handleStartUpdate(value) {
            this.segment.start = value;
            this.segment.dirty = true;
        },
        handleEndUpdate(value) {
            this.segment.end = value;
            this.segment.dirty = true;
        },
    },
    template: `
    <div class="segment u-mb-small"
        :class="{'segment--active': active, 'segment--current': isCurrent}"
        ref="container">
        <header class="segment__header">
            <button class="segment__id" type="button"
                @click="$emit('activateSegment', index)">#{{formattedID}}</button>
            <button type="button" class=""
                @click="play">▶</button>
            <Timecode-Input :seconds="segment.start" @submit="handleStartUpdate" />–<Timecode-Input :seconds="segment.end" @submit="handleEndUpdate" />
            <span class="segment__extra">{{segment.speaker}}</span>
            <button type="button" class="segment__action"
                @click="insert">+</button>
            <button type="button" class="segment__action"
                @click="remove">&times;</button>
        </header>
        <p class="segment__text u-ll" :class="{'segment__text--dirty': isDirty}">
            <TranscriptWord v-for="(word, idx) in segment.words"
                :key="word.id"
                :segmentIndex="index"
                :index="idx"
                :word="word"
                :showConfidence="showConfidence" />
        </p>
    </div>
    `,
};
