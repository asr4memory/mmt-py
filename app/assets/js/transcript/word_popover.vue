<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { computed, onBeforeUnmount, onMounted, ref, toRef } from "vue";
import ChevronLeftIcon from "../icons/chevron_left_icon.vue";
import ChevronRightIcon from "../icons/chevron_right_icon.vue";
import CloseIcon from "../icons/close_icon.vue";
import InsertLeftIcon from "../icons/insert_left_icon.vue";
import InsertRightIcon from "../icons/insert_right_icon.vue";
import StrikethroughIcon from "../icons/strikethrough_icon.vue";
import TagIcon from "../icons/tag_icon.vue";
import TrashIcon from "../icons/trash_icon.vue";
import { ENTITY_LABELS, entityMeta } from "./entities";
import TimecodeRange from "./timecode_range.vue";
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

// Entity info, present only when the word is part of a named-entity mention.
const mention = computed(() => store.mention(props.word.mentionId));

const entityMetaInfo = computed(() => entityMeta(mention.value?.label));

// Options for the type selector: the known labels, plus the mention's own
// label first if it happens to be outside the known tagset.
const entityOptions = computed(() => {
    const labels = [...ENTITY_LABELS];
    const current = mention.value?.label;
    if (current && !labels.includes(current)) {
        labels.unshift(current);
    }
    return labels.map((label) => ({
        value: label,
        nameKey: entityMeta(label)?.nameKey ?? null,
    }));
});

const entityText = computed(() =>
    store.mentionText(props.segmentIndex, props.word.mentionId),
);

// The span this mention covers within its segment, used to decide whether it
// can grow further left or right.
const mentionBounds = computed(() => {
    const segment = store.segments[props.segmentIndex];
    const id = props.word.mentionId;
    if (!segment || !id) return null;
    const indices = segment.words
        .map((word, i) => (word.mentionId === id ? i : -1))
        .filter((i) => i >= 0);
    if (indices.length === 0) return null;
    return {
        words: segment.words,
        left: indices[0],
        right: indices[indices.length - 1],
    };
});

const canExtendLeft = computed(() => {
    const b = mentionBounds.value;
    return !!b && b.left > 0 && !b.words[b.left - 1].mentionId;
});

const canExtendRight = computed(() => {
    const b = mentionBounds.value;
    return (
        !!b && b.right < b.words.length - 1 && !b.words[b.right + 1].mentionId
    );
});

// Trimming either end is possible only while the span holds more than one
// word; removing the last word is what the remove action is for.
const canReduce = computed(() => {
    const b = mentionBounds.value;
    return !!b && b.right > b.left;
});

const formattedEntityScore = computed(() =>
    mention.value
        ? mention.value.score.toLocaleString(
              document.documentElement.lang || undefined,
          )
        : "",
);

// Redaction info, present only when the word is part of a redacted run. The
// redaction tier is independent of the mention tier: a word may carry both.
const redaction = computed(() => store.redaction(props.word.redactionId));

const redactionText = computed(() =>
    store.redactionText(props.segmentIndex, props.word.redactionId),
);

const redactionReason = computed(() => redaction.value?.reason ?? "");

// The run this redaction covers within its segment, used to decide whether it
// can grow or shrink further.
const redactionBounds = computed(() => {
    const segment = store.segments[props.segmentIndex];
    const id = props.word.redactionId;
    if (!segment || !id) return null;
    const indices = segment.words
        .map((word, i) => (word.redactionId === id ? i : -1))
        .filter((i) => i >= 0);
    if (indices.length === 0) return null;
    return {
        words: segment.words,
        left: indices[0],
        right: indices[indices.length - 1],
    };
});

const canExtendRedactionLeft = computed(() => {
    const b = redactionBounds.value;
    return !!b && b.left > 0 && !b.words[b.left - 1].redactionId;
});

const canExtendRedactionRight = computed(() => {
    const b = redactionBounds.value;
    return (
        !!b && b.right < b.words.length - 1 && !b.words[b.right + 1].redactionId
    );
});

// Shortening either end is possible only while the run holds more than one
// word; unlinking the last word is what the remove action is for.
const canReduceRedaction = computed(() => {
    const b = redactionBounds.value;
    return !!b && b.right > b.left;
});

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

function handleRemoveMention() {
    if (props.word.mentionId) {
        store.removeMention(props.segmentIndex, props.word.mentionId);
    }
    emit("close");
}

function handleTypeChange(event: Event) {
    const label = (event.target as HTMLSelectElement).value;
    if (props.word.mentionId) {
        store.setMentionLabel(props.segmentIndex, props.word.mentionId, label);
    }
}

function handleCreateMention() {
    // We cannot know the entity type, so start from a default the user can
    // correct with the type selector that appears once the mention exists.
    store.createMention(props.segmentIndex, props.index, ENTITY_LABELS[0]);
}

function handleExtendLeft() {
    if (props.word.mentionId) {
        store.extendMention(props.segmentIndex, props.word.mentionId, "left");
    }
}

function handleExtendRight() {
    if (props.word.mentionId) {
        store.extendMention(props.segmentIndex, props.word.mentionId, "right");
    }
}

function handleReduceLeft() {
    if (props.word.mentionId) {
        store.reduceMention(props.segmentIndex, props.word.mentionId, "left");
    }
}

function handleReduceRight() {
    if (props.word.mentionId) {
        store.reduceMention(props.segmentIndex, props.word.mentionId, "right");
    }
}

function handleCreateRedaction() {
    store.createRedaction(props.segmentIndex, props.index);
}

function handleRemoveRedaction() {
    if (props.word.redactionId) {
        store.removeRedaction(props.segmentIndex, props.word.redactionId);
    }
}

function handleExtendRedactionLeft() {
    if (props.word.redactionId) {
        store.extendRedaction(
            props.segmentIndex,
            props.word.redactionId,
            "left",
        );
    }
}

function handleExtendRedactionRight() {
    if (props.word.redactionId) {
        store.extendRedaction(
            props.segmentIndex,
            props.word.redactionId,
            "right",
        );
    }
}

function handleReduceRedactionLeft() {
    if (props.word.redactionId) {
        store.reduceRedaction(
            props.segmentIndex,
            props.word.redactionId,
            "left",
        );
    }
}

function handleReduceRedactionRight() {
    if (props.word.redactionId) {
        store.reduceRedaction(
            props.segmentIndex,
            props.word.redactionId,
            "right",
        );
    }
}

function handleReasonInput(event: Event) {
    const reason = (event.target as HTMLInputElement).value;
    if (props.word.redactionId) {
        store.setRedactionReason(props.word.redactionId, reason);
    }
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

            <!-- word: heading + editing actions, then word details -->
            <div class="popup__section">
                <div class="popup__section-head">
                    <h3 class="popup__heading">{{ $t("word_section") }}</h3>
                    <div class="popup__actions">
                        <button @click="handleLeftInsert" class="popup__btn" :title="$t('add_word_left')"
                            :aria-label="$t('add_word_left')">
                            <InsertLeftIcon />
                        </button>
                        <button @click="handleRightInsert" class="popup__btn" :title="$t('add_word_right')"
                            :aria-label="$t('add_word_right')">
                            <InsertRightIcon />
                        </button>
                        <button @click="handleRemove" class="popup__btn popup__btn--danger" :title="$t('remove_word')"
                            :aria-label="$t('remove_word')">
                            <TrashIcon />
                        </button>
                    </div>
                </div>
                <p class="popup__title">{{ word.word }}</p>
                <div class="popup__info">
                    <div class="popup__row">
                        <span class="popup__label">{{ $t("timestamps") }}</span>
                        <span class="popup__value">
                            <TimecodeRange :start="word.start" :end="word.end" />
                        </span>
                    </div>
                    <div class="popup__row">
                        <span class="popup__label">{{ $t("confidence") }}</span>
                        <span class="popup__conf">
                            <meter class="popup__meter" :value="word.score" min="0" max="1"></meter>
                            <span class="popup__score">{{ formattedScore }}</span>
                        </span>
                    </div>
                </div>
            </div>

            <!-- mention: entity info, only when the word is part of a mention -->
            <template v-if="mention">
                <div class="popup__divider"></div>
                <div class="popup__section">
                    <div class="popup__section-head">
                        <h3 class="popup__heading">{{ $t("mention_section") }}</h3>
                        <div class="popup__actions">
                            <!-- left edge: + (outer) grows it, − (inner) trims it -->
                            <span class="popup__btn-pair">
                                <button @click="handleExtendLeft" class="popup__btn" :disabled="!canExtendLeft"
                                    :title="$t('extend_mention_left')" :aria-label="$t('extend_mention_left')">
                                    <ChevronLeftIcon />
                                </button>
                                <button @click="handleReduceLeft" class="popup__btn" :disabled="!canReduce"
                                    :title="$t('reduce_mention_left')" :aria-label="$t('reduce_mention_left')">
                                    <ChevronRightIcon />
                                </button>
                            </span>
                            <!-- right edge: − (inner) trims it, + (outer) grows it -->
                            <span class="popup__btn-pair">
                                <button @click="handleReduceRight" class="popup__btn" :disabled="!canReduce"
                                    :title="$t('reduce_mention_right')" :aria-label="$t('reduce_mention_right')">
                                    <ChevronLeftIcon />
                                </button>
                                <button @click="handleExtendRight" class="popup__btn" :disabled="!canExtendRight"
                                    :title="$t('extend_mention_right')" :aria-label="$t('extend_mention_right')">
                                    <ChevronRightIcon />
                                </button>
                            </span>
                            <button @click="handleRemoveMention" class="popup__btn"
                                :title="$t('remove_mention')" :aria-label="$t('remove_mention')">
                                <CloseIcon />
                            </button>
                        </div>
                    </div>
                    <p class="popup__title">{{ entityText }}</p>
                    <div class="popup__info">
                        <div class="popup__row">
                            <span class="popup__label">{{ $t("entity_type") }}</span>
                            <select
                                class="popup__select"
                                :value="mention.label"
                                :aria-label="$t('entity_type')"
                                @change="handleTypeChange"
                            >
                                <option v-for="opt in entityOptions" :key="opt.value" :value="opt.value">
                                    {{ opt.nameKey ? $t(opt.nameKey) : opt.value }}
                                </option>
                            </select>
                        </div>
                        <div class="popup__row">
                            <span class="popup__label">{{ $t("mention_confidence") }}</span>
                            <span class="popup__conf">
                                <meter class="popup__meter" :value="mention.score" min="0" max="1"></meter>
                                <span class="popup__score">{{ formattedEntityScore }}</span>
                            </span>
                        </div>
                    </div>
                </div>
            </template>

            <!-- no mention yet: offer to tag this word as one -->
            <template v-else>
                <div class="popup__divider"></div>
                <div class="popup__section">
                    <div class="popup__section-head">
                        <h3 class="popup__heading">{{ $t("mention_section") }}</h3>
                        <div class="popup__actions">
                            <button @click="handleCreateMention" class="popup__btn"
                                :title="$t('set_as_mention')" :aria-label="$t('set_as_mention')">
                                <TagIcon />
                            </button>
                        </div>
                    </div>
                    <p class="popup__empty">{{ $t("no_mention") }}</p>
                </div>
            </template>

            <!-- redaction: the run this word belongs to, when it has one -->
            <template v-if="redaction">
                <div class="popup__divider"></div>
                <div class="popup__section">
                    <div class="popup__section-head">
                        <h3 class="popup__heading">{{ $t("redaction_section") }}</h3>
                        <div class="popup__actions">
                            <!-- left edge: + (outer) grows it, − (inner) shortens it -->
                            <span class="popup__btn-pair">
                                <button @click="handleExtendRedactionLeft" class="popup__btn"
                                    :disabled="!canExtendRedactionLeft"
                                    :title="$t('extend_redaction_left')" :aria-label="$t('extend_redaction_left')">
                                    <ChevronLeftIcon />
                                </button>
                                <button @click="handleReduceRedactionLeft" class="popup__btn"
                                    :disabled="!canReduceRedaction"
                                    :title="$t('reduce_redaction_left')" :aria-label="$t('reduce_redaction_left')">
                                    <ChevronRightIcon />
                                </button>
                            </span>
                            <!-- right edge: − (inner) shortens it, + (outer) grows it -->
                            <span class="popup__btn-pair">
                                <button @click="handleReduceRedactionRight" class="popup__btn"
                                    :disabled="!canReduceRedaction"
                                    :title="$t('reduce_redaction_right')" :aria-label="$t('reduce_redaction_right')">
                                    <ChevronLeftIcon />
                                </button>
                                <button @click="handleExtendRedactionRight" class="popup__btn"
                                    :disabled="!canExtendRedactionRight"
                                    :title="$t('extend_redaction_right')" :aria-label="$t('extend_redaction_right')">
                                    <ChevronRightIcon />
                                </button>
                            </span>
                            <button @click="handleRemoveRedaction" class="popup__btn"
                                :title="$t('remove_redaction')" :aria-label="$t('remove_redaction')">
                                <CloseIcon />
                            </button>
                        </div>
                    </div>
                    <p class="popup__title">{{ redactionText }}</p>
                    <div class="popup__info">
                        <div class="popup__row">
                            <span class="popup__label">{{ $t("redaction_reason") }}</span>
                            <input
                                class="popup__input"
                                type="text"
                                :value="redactionReason"
                                :aria-label="$t('redaction_reason')"
                                @input="handleReasonInput"
                            />
                        </div>
                    </div>
                </div>
            </template>

            <!-- not redacted yet: offer to redact this word -->
            <template v-else>
                <div class="popup__divider"></div>
                <div class="popup__section">
                    <div class="popup__section-head">
                        <h3 class="popup__heading">{{ $t("redaction_section") }}</h3>
                        <div class="popup__actions">
                            <button @click="handleCreateRedaction" class="popup__btn"
                                :title="$t('set_as_redaction')" :aria-label="$t('set_as_redaction')">
                                <StrikethroughIcon />
                            </button>
                        </div>
                    </div>
                    <p class="popup__empty">{{ $t("no_redaction") }}</p>
                </div>
            </template>
        </div>
    </Teleport>
</template>
