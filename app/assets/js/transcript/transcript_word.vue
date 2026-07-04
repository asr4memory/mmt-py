<script setup lang="ts">
import { computed, nextTick, ref, useTemplateRef } from "vue";
import seekAndPlay from "./seek_and_play";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptWord } from "./types";
import WordPopover from "./word_popover.vue";

const props = defineProps<{
    segmentIndex: number;
    index: number;
    word: TranscriptWord;
    isActive?: boolean;
    isMentionStart?: boolean;
    isMentionEnd?: boolean;
    showConfidence?: boolean;
    showEntities?: boolean;
    showEdits?: boolean;
}>();

const store = useTranscriptStore();

const wordEl = useTemplateRef<HTMLSpanElement>("word");

const editMode = ref(false);
const popoverOpen = ref(false);

const backgroundColor = computed(
    () =>
        `hsl(from var(--color-confidence-base) h s l / ${1 - props.word.score})`,
);

const wordStyle = computed(() => {
    const style: Record<string, string> = {};
    if (props.showConfidence) {
        style["background-color"] = backgroundColor.value;
    }
    return style;
});

// The word's NER label, or null when it is not part of a mention (or entity
// display is off). Drives the entity styling via the data-entity attribute.
const mentionLabel = computed(() =>
    props.showEntities ? store.mentionLabel(props.word.mentionId) : null,
);

function handleFocus(event: FocusEvent) {
    editMode.value = true;
    const span = event.target as HTMLSpanElement;
    nextTick(() => {
        const input = span.firstElementChild as HTMLInputElement | null;
        input?.focus();
    });
}

function handleInputBlur(event: Event) {
    const input = event.target as HTMLInputElement;
    store.updateWord(props.segmentIndex, props.index, input.value);
    nextTick(() => {
        editMode.value = false;
    });
}

function handleEnterKey(event: KeyboardEvent) {
    const input = event.target as HTMLInputElement;
    const span = input.parentElement;
    const next = span?.nextElementSibling as HTMLElement | null;
    if (next) {
        next.focus();
    } else {
        editMode.value = false;
        store.updateWord(props.segmentIndex, props.index, input.value);
    }
}

function play() {
    const player = document.getElementById(
        "media-player",
    ) as HTMLMediaElement | null;
    if (player) {
        seekAndPlay(player, props.word.start);
    }
}
</script>

<template>
    <span
        class="transcript-word"
        :class="{
            'transcript-word--active': isActive,
            'transcript-word--dirty': word.dirty && showEdits,
            'transcript-word--entity': mentionLabel !== null,
            'transcript-word--entity-start': mentionLabel !== null && isMentionStart,
            'transcript-word--entity-end': mentionLabel !== null && isMentionEnd,
        }"
        :data-entity="mentionLabel ?? undefined"
        :tabindex="editMode ? -1 : 0"
        :style="wordStyle"
        ref="word"
        @focus="handleFocus"
        @click.shift="play"
    >
        {{ word.word }}
        <input
            v-if="editMode"
            class="transcript-word__input"
            tabindex="0"
            :value="word.word"
            @blur="handleInputBlur"
            @click.shift="play"
            @keyup.enter="handleEnterKey"
        />
        <button
            v-if="!editMode"
            type="button"
            class="transcript-word__trigger"
            :title="$t('word_actions')"
            @click="popoverOpen = !popoverOpen"
        >
            ⋯
        </button>
        <WordPopover
            v-if="popoverOpen"
            :segment-index="segmentIndex"
            :index="index"
            :word="word"
            :reference="wordEl"
            @close="popoverOpen = false"
        />
    </span>
</template>
