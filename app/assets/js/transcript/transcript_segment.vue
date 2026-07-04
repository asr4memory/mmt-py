<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref, useTemplateRef, watch } from "vue";
import seekAndPlay from "./seek_and_play";
import seekMedia from "./seek_media";
import SegmentPopover from "./segment_popover.vue";
import SpeakerSelect from "./speaker_select.vue";
import TimecodeRange from './timecode_range.vue';
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

const emit = defineEmits<{ "activate-segment": [index: number] }>();

const store = useTranscriptStore();
const { speakers } = storeToRefs(store);

const container = useTemplateRef<HTMLDivElement>("container");
const trigger = useTemplateRef<HTMLButtonElement>("trigger");

const popoverOpen = ref(false);

const isDirty = computed(
    () =>
        props.segment.dirty === true ||
        props.segment.words.some((word) => word.dirty === true),
);

// For each word, whether it begins or ends a named entity mention. A mention
// boundary is where mentionId changes; mentions do not cross segment edges.
const mentionBoundaries = computed(() =>
    props.segment.words.map((word, idx) => {
        const words = props.segment.words;
        const hasMention = word.mentionId != null;
        return {
            isMentionStart:
                hasMention && words[idx - 1]?.mentionId !== word.mentionId,
            isMentionEnd:
                hasMention && words[idx + 1]?.mentionId !== word.mentionId,
        };
    }),
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

function mediaPlayer() {
    return document.getElementById("media-player") as HTMLMediaElement | null;
}

function play() {
    const player = mediaPlayer();
    if (player) {
        seekAndPlay(player, props.segment.start);
    }
}

function activate() {
    emit("activate-segment", props.index);
    const player = mediaPlayer();
    if (player) {
        seekMedia(player, props.segment.start);
    }
}

function handleSpeakerUpdate(value: string | null) {
    props.segment.speakerId = value;
    props.segment.dirty = true;
}
</script>

<template>
    <div
        class="transcript-segment u-mb-large"
        :class="{
            'transcript-segment--active': active,
            'transcript-segment--current': isCurrent,
        }"
        ref="container"
    >
        <aside class="transcript-segment__meta">
            <SpeakerSelect
            v-if="speakers.length > 0"
            :modelValue="segment.speakerId ?? undefined"
            :speakers="speakers"
            :segmentId="segment.id"
            @update:modelValue="handleSpeakerUpdate"
            />
            <div class="transcript-segment__timecode-row">
                <button
                    type="button"
                    class="transcript-segment__trigger"
                    ref="trigger"
                    :title="$t('segment_actions')"
                    :aria-label="$t('segment_actions')"
                    @click="popoverOpen = !popoverOpen"
                >
                    ⋯
                </button>
                <button
                    type="button"
                    class="transcript-segment__timecode"
                    @click="activate"
                    @dblclick="play"
                >
                    <TimecodeRange :start="segment.start" :end="segment.end"/>
                </button>
            </div>
            <SegmentPopover
                v-if="popoverOpen"
                :segment="segment"
                :reference="trigger"
                @close="popoverOpen = false"
            />
        </aside>
        <p
            class="transcript-segment__text"
            :class="{ 'transcript-segment__text--dirty': isDirty && showEdits }"
        >
            <TranscriptWord
                v-for="(word, idx) in segment.words"
                :key="word.id"
                :segmentIndex="index"
                :index="idx"
                :word="word"
                :isActive="idx === currentWordIdx"
                :isMentionStart="mentionBoundaries[idx].isMentionStart"
                :isMentionEnd="mentionBoundaries[idx].isMentionEnd"
                :showConfidence="showConfidence"
                :showEntities="showEntities"
                :showEdits="showEdits"
            />
        </p>
    </div>
</template>
