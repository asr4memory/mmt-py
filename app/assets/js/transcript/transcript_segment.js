import { mapState, mapActions } from "pinia";

import { useTranscriptStore } from "./transcript_store";
import TimecodeInput from "./timecode_input";
import TranscriptWord from "./transcript_word";
import SpeakerSelect from "./speaker_select.ts";
import formatTimecode from "../shared/format_timecode";
import seekAndPlay from "./seek_and_play";

export default {
    components: {
        TimecodeInput,
        TranscriptWord,
        SpeakerSelect,
    },
    name: "TranscriptSegment",
    props: {
        index: Number,
        segment: Object,
        isCurrent: Boolean,
        currentWordIdx: Number,
        active: Boolean,
        showConfidence: Boolean,
        showEntities: Boolean,
        showEdits: Boolean,
        autoScroll: Boolean,
    },
    emits: ["activate-segment"],
    computed: {
        ...mapState(useTranscriptStore, ["speakers"]),
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
        handleSpeakerUpdate(value) {
            this.segment.speaker = value;
            this.segment.dirty = true;
        },
    },
    template: `
    <div class="transcript-segment u-mb-small"
        :class="{'transcript-segment--active': active, 'transcript-segment--current': isCurrent}"
        ref="container">
        <header class="transcript-segment__header">
            <button class="transcript-segment__id" type="button"
                @click="$emit('activate-segment', index)">#{{formattedID}}</button>
            <button type="button" class="transcript-button"
                @click="play"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 4.8 L18.6 12 L7 19.2 Z" /></svg></button>
            <Timecode-Input :seconds="segment.start" @submit="handleStartUpdate" />–<Timecode-Input :seconds="segment.end" @submit="handleEndUpdate" />
            <SpeakerSelect :modelValue="segment.speaker" :speakers="speakers" :segmentId="String(segment.id)" @update:modelValue="handleSpeakerUpdate" />
            <button type="button" class="transcript-button"
                @click="insert">+</button>
            <button type="button" class="transcript-button"
                @click="remove">&times;</button>
        </header>
        <p class="transcript-segment__text u-ll" :class="{'transcript-segment__text--dirty': isDirty && showEdits}">
            <TranscriptWord v-for="(word, idx) in segment.words"
                :key="word.id"
                :segmentIndex="index"
                :index="idx"
                :word="word"
                :isActive="idx === currentWordIdx"
                :showConfidence="showConfidence"
                :showEntities="showEntities"
                :showEdits="showEdits" />

        </p>
    </div>
    `,
};
