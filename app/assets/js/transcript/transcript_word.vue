<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef } from "vue";
import seekAndPlay from "./seek_and_play";
import TimeCode from "./time_code.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptWord } from "./types";

const props = defineProps<{
    segmentIndex: number;
    index: number;
    word: TranscriptWord;
    isActive?: boolean;
    showConfidence?: boolean;
    showEntities?: boolean;
    showEdits?: boolean;
}>();

const store = useTranscriptStore();

const wordEl = useTemplateRef<HTMLSpanElement>("word");
const popover = useTemplateRef<HTMLDivElement>("popover");

const editMode = ref(false);

const backgroundColor = computed(
    () => `hsl(208 71% 77% / ${1 - props.word.score})`,
);

const anchorName = computed(
    // Must be unique per word: the popover is in the top layer, where a name
    // shared by all words would resolve to the last word in the document.
    () => `--word-${props.segmentIndex}-${props.index}`,
);

const wordStyle = computed(() => {
    const style: Record<string, string> = { "anchor-name": anchorName.value };
    if (props.showConfidence) {
        style["background-color"] = backgroundColor.value;
    }
    return style;
});

const formattedScore = computed(() =>
    // Word confidence score.
    props.word.score.toLocaleString(document.documentElement.lang),
);

const speakerName = computed(() => {
    if (!props.word.speakerId) return "";
    return (
        store.speakers.find((s) => s.id === props.word.speakerId)?.name ?? ""
    );
});

const entityClass = computed(() => {
    switch (props.word.ner_entity) {
        case "ORG":
            return "transcript-word--org";
        case "PER":
            return "transcript-word--per";
        case "DATE":
            return "transcript-word--date";
        case "LOC":
            return "transcript-word--loc";
        default:
            return "";
    }
});

onBeforeUnmount(() => {
    window.removeEventListener("scroll", handleScroll, { capture: true });
});

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

function handleMouseOver() {
    if (popover.value && !popover.value.matches(":popover-open")) {
        popover.value.showPopover({ source: wordEl.value ?? undefined });
        positionPopoverFallback();
        // Anchored popovers do not reliably track their anchor across scrolls
        // (mouse wheel, auto-scroll during playback), so hide on the first
        // scroll instead.
        window.addEventListener("scroll", handleScroll, {
            capture: true,
            passive: true,
        });
    }
}

function positionPopoverFallback() {
    // Browsers without CSS anchor positioning render the popover at its static
    // position (the line below the word), so place it next to the word
    // manually.
    if (
        CSS.supports("position-anchor", "--word") &&
        CSS.supports("position-area", "bottom")
    ) {
        return;
    }
    if (!popover.value || !wordEl.value) return;
    const wordRect = wordEl.value.getBoundingClientRect();
    const popoverRect = popover.value.getBoundingClientRect();
    let top = wordRect.bottom;
    if (top + popoverRect.height > window.innerHeight) {
        top = wordRect.top - popoverRect.height;
    }
    let left = wordRect.left + (wordRect.width - popoverRect.width) / 2;
    left = Math.max(0, Math.min(left, window.innerWidth - popoverRect.width));
    popover.value.style.top = `${top}px`;
    popover.value.style.left = `${left}px`;
}

function handleMouseOut() {
    hidePopover();
}

function handleScroll() {
    hidePopover();
}

function hidePopover() {
    if (popover.value?.matches(":popover-open")) {
        popover.value.hidePopover();
    }
    window.removeEventListener("scroll", handleScroll, { capture: true });
}

function play() {
    const player = document.getElementById(
        "media-player",
    ) as HTMLMediaElement | null;
    if (player) {
        seekAndPlay(player, props.word.start);
    }
}

function handleLeftInsert() {
    store.insertLeft(props.segmentIndex, props.index);
}

function handleRightInsert() {
    store.insertRight(props.segmentIndex, props.index);
}

function handleRemove() {
    store.deleteWord(props.segmentIndex, props.index);
}
</script>

<template>
    <span
        class="transcript-word"
        :class="[
            {
                'transcript-word--active': isActive,
                'transcript-word--dirty': word.dirty && showEdits,
            },
            showEntities ? entityClass : '',
        ]"
        :tabindex="editMode ? -1 : 0"
        :style="wordStyle"
        ref="word"
        @mouseover="handleMouseOver"
        @mouseout="handleMouseOut"
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
        <div
            v-if="!editMode"
            popover="hint"
            ref="popover"
            class="popover"
            :style="{ 'position-anchor': anchorName }"
        >
            <header class="popover__header">
                <button
                    type="button"
                    :title="$t('add_word_left')"
                    @click="handleLeftInsert"
                >
                    +
                </button>
                <button
                    type="button"
                    :title="$t('remove_word')"
                    @click="handleRemove"
                >
                    &times;
                </button>
                <button
                    type="button"
                    :title="$t('add_word_right')"
                    @click="handleRightInsert"
                >
                    +
                </button>
            </header>
            <hr />
            <TimeCode :seconds="word.start" />–<TimeCode :seconds="word.end" /><br />
            {{ speakerName }}<br v-if="speakerName" />
            {{ $t("score") }} {{ formattedScore }}
        </div>
    </span>
</template>
