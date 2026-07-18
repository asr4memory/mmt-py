<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { onBeforeUnmount, onMounted, ref, toRef } from "vue";
import InsertSegmentAfterIcon from "../icons/insert_segment_after_icon.vue";
import InsertSegmentBeforeIcon from "../icons/insert_segment_before_icon.vue";
import TrashIcon from "../icons/trash_icon.vue";
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
                            <InsertSegmentBeforeIcon />
                        </button>
                        <button @click="handleInsertAfter" class="popup__btn" :title="$t('add_segment_after')"
                            :aria-label="$t('add_segment_after')">
                            <InsertSegmentAfterIcon />
                        </button>
                        <button @click="handleDelete" class="popup__btn popup__btn--danger" :title="$t('delete_segment')"
                            :aria-label="$t('delete_segment')">
                            <TrashIcon />
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
