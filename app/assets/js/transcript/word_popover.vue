<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { computed, onBeforeUnmount, onMounted, ref, toRef } from "vue";
import TimeCode from "./time_code.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptWord } from "./types";

const props = defineProps<{
    segmentIndex: number;
    index: number;
    word: TranscriptWord;
    reference: HTMLElement | null;
}>();

const emit = defineEmits<{ close: [] }>();

const store = useTranscriptStore();

const floating = ref<HTMLDivElement | null>(null);

const { floatingStyles } = useFloating(toRef(props, "reference"), floating, {
    placement: "bottom",
    middleware: [offset(4), flip(), shift({ padding: 4 })],
    whileElementsMounted: autoUpdate,
});

const speakerName = computed(() => {
    if (!props.word.speakerId) return "";
    return (
        store.speakers.find((s) => s.id === props.word.speakerId)?.name ?? ""
    );
});

const formattedScore = computed(() =>
    props.word.score.toLocaleString(document.documentElement.lang || undefined),
);

function handleLeftInsert() {
    store.insertLeft(props.segmentIndex, props.index);
    emit("close");
}

function handleRightInsert() {
    store.insertRight(props.segmentIndex, props.index);
    emit("close");
}

function handleRemove() {
    store.deleteWord(props.segmentIndex, props.index);
    emit("close");
}

function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
        emit("close");
    }
}

function handlePointerDown(event: PointerEvent) {
    const target = event.target as Node | null;
    if (
        target &&
        (floating.value?.contains(target) || props.reference?.contains(target))
    ) {
        return;
    }
    emit("close");
}

onMounted(() => {
    document.addEventListener("keydown", handleKeydown);
    document.addEventListener("pointerdown", handlePointerDown);
});

onBeforeUnmount(() => {
    document.removeEventListener("keydown", handleKeydown);
    document.removeEventListener("pointerdown", handlePointerDown);
});
</script>

<template>
    <Teleport to="body">
        <div ref="floating" class="popover" :style="floatingStyles">
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
    </Teleport>
</template>
