<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, useTemplateRef, watch } from "vue";
import seekAndPlay from "./seek_and_play";
import SpeakerSelect from "./speaker_select.vue";
import TimecodeInput from "./timecode_input.vue";
import { useTranscriptStore } from "./transcript_store";
import TranscriptWord from "./transcript_word.vue";
import type { TranscriptSegment } from "./types";

const props = defineProps<{
    index: number;
    segment: TranscriptSegment;
    isCurrent?: boolean;
    currentWordIdx?: number;
    active?: boolean;
    showConfidence?: boolean;
    showEntities?: boolean;
    showEdits?: boolean;
    autoScroll?: boolean;
}>();

defineEmits<{ "activate-segment": [index: number] }>();

const store = useTranscriptStore();
const { speakers } = storeToRefs(store);

const container = useTemplateRef<HTMLDivElement>("container");

const formattedID = computed(() => String(props.segment.id).padStart(3, "0"));

const isDirty = computed(
    () =>
        props.segment.dirty === true ||
        props.segment.words.some((word) => word.dirty === true),
);

watch(
    () => props.isCurrent,
    (newValue) => {
        if (props.autoScroll && newValue === true) {
            container.value?.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });
        }
    },
);

function play() {
    const player = document.getElementById(
        "media-player",
    ) as HTMLMediaElement | null;
    if (player) {
        seekAndPlay(player, props.segment.start);
    }
}

function insert() {
    store.insertSegmentBefore("newSegment", props.segment.id);
}

function remove() {
    store.deleteSegment(props.segment.id);
}

function handleStartUpdate(value: number) {
    props.segment.start = value;
    props.segment.dirty = true;
}

function handleEndUpdate(value: number) {
    props.segment.end = value;
    props.segment.dirty = true;
}

function handleSpeakerUpdate(value: string) {
    props.segment.speakerId = value;
    props.segment.dirty = true;
}
</script>

<template>
    <div
        class="transcript-segment u-mb-small"
        :class="{
            'transcript-segment--active': active,
            'transcript-segment--current': isCurrent,
        }"
        ref="container"
    >
        <header class="transcript-segment__header">
            <div class="transcript-segment__actions">
                <button
                    class="transcript-segment__id"
                    type="button"
                    @click="$emit('activate-segment', index)"
                >
                    #{{ formattedID }}
                </button>
                <button type="button" class="transcript-button" @click="play">
                    <svg
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        aria-hidden="true"
                    >
                        <path d="M7 4.8 L18.6 12 L7 19.2 Z" />
                    </svg>
                </button>
                <button
                    type="button"
                    class="transcript-button"
                    @click="insert"
                >
                    +
                </button>
                <button
                    type="button"
                    class="transcript-button"
                    @click="remove"
                >
                    &times;
                </button>
            </div>
            <div class="transcript-segment__timecodes">
                <TimecodeInput
                    :seconds="segment.start"
                    @submit="handleStartUpdate"
                />–<TimecodeInput
                    :seconds="segment.end"
                    @submit="handleEndUpdate"
                />
            </div>
            <SpeakerSelect
                v-if="speakers.length > 0"
                :modelValue="segment.speakerId ?? undefined"
                :speakers="speakers"
                :segmentId="String(segment.id)"
                @update:modelValue="handleSpeakerUpdate"
            />
        </header>
        <p
            class="transcript-segment__text u-ll"
            :class="{ 'transcript-segment__text--dirty': isDirty && showEdits }"
        >
            <TranscriptWord
                v-for="(word, idx) in segment.words"
                :key="word.id"
                :segmentIndex="index"
                :index="idx"
                :word="word"
                :isActive="idx === currentWordIdx"
                :showConfidence="showConfidence"
                :showEntities="showEntities"
                :showEdits="showEdits"
            />
        </p>
    </div>
</template>
