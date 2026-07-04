<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { onBeforeUnmount, onMounted, ref, toRef } from "vue";
import TimecodeInput from "./timecode_input.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptSegment } from "./types";

const props = defineProps<{
    segment: TranscriptSegment;
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

function handleInsertBefore() {
    store.insertSegmentBefore("newSegment", props.segment.id);
    emit("close");
}

function handleInsertAfter() {
    store.insertSegmentAfter("newSegment", props.segment.id);
    emit("close");
}

function handleDelete() {
    store.deleteSegment(props.segment.id);
    emit("close");
}

function handleStartUpdate(value: number) {
    props.segment.start = value;
    props.segment.dirty = true;
}

function handleEndUpdate(value: number) {
    props.segment.end = value;
    props.segment.dirty = true;
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
        <div ref="floating" class="popup" :style="floatingStyles">
            <div class="popup__caret"></div>

            <!-- segment: heading + structure actions, then editable timecodes -->
            <div class="popup__section">
                <div class="popup__section-head">
                    <h3 class="popup__heading">{{ $t("segment_section") }}</h3>
                    <div class="popup__actions">
                        <button @click="handleInsertBefore" class="popup__btn" :title="$t('add_segment_before')"
                            :aria-label="$t('add_segment_before')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="4" y1="5" x2="20" y2="5" />
                                <line x1="12" y1="11" x2="12" y2="19" />
                                <line x1="8" y1="15" x2="16" y2="15" />
                            </svg>
                        </button>
                        <button @click="handleInsertAfter" class="popup__btn" :title="$t('add_segment_after')"
                            :aria-label="$t('add_segment_after')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="12" y1="5" x2="12" y2="13" />
                                <line x1="8" y1="9" x2="16" y2="9" />
                                <line x1="4" y1="19" x2="20" y2="19" />
                            </svg>
                        </button>
                        <button @click="handleDelete" class="popup__btn popup__btn--danger" :title="$t('delete_segment')"
                            :aria-label="$t('delete_segment')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M5 7h14" />
                                <path d="M9 7V5h6v2" />
                                <path d="M7.3 7l1 13h7.4l1-13" />
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="popup__info">
                    <div class="popup__row">
                        <span class="popup__label">{{ $t("segment_start") }}</span>
                        <span class="popup__value">
                            <TimecodeInput
                                :seconds="segment.start"
                                @submit="handleStartUpdate"
                            />
                        </span>
                    </div>
                    <div class="popup__row">
                        <span class="popup__label">{{ $t("segment_end") }}</span>
                        <span class="popup__value">
                            <TimecodeInput
                                :seconds="segment.end"
                                @submit="handleEndUpdate"
                            />
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>
