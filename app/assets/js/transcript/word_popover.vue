<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { computed, onBeforeUnmount, onMounted, ref, toRef } from "vue";
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
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="4" y1="4" x2="4" y2="20" />
                                <line x1="9.5" y1="12" x2="19" y2="12" />
                                <line x1="14.25" y1="7.5" x2="14.25" y2="16.5" />
                            </svg>
                        </button>
                        <button @click="handleRightInsert" class="popup__btn" :title="$t('add_word_right')"
                            :aria-label="$t('add_word_right')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="20" y1="4" x2="20" y2="20" />
                                <line x1="5" y1="12" x2="14.5" y2="12" />
                                <line x1="9.75" y1="7.5" x2="9.75" y2="16.5" />
                            </svg>
                        </button>
                        <button @click="handleRemove" class="popup__btn popup__btn--danger" :title="$t('remove_word')"
                            :aria-label="$t('remove_word')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M5 7h14" />
                                <path d="M9 7V5h6v2" />
                                <path d="M7.3 7l1 13h7.4l1-13" />
                            </svg>
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
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="m15 18-6-6 6-6" />
                                    </svg>
                                </button>
                                <button @click="handleReduceLeft" class="popup__btn" :disabled="!canReduce"
                                    :title="$t('reduce_mention_left')" :aria-label="$t('reduce_mention_left')">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="m9 18 6-6-6-6" />
                                    </svg>
                                </button>
                            </span>
                            <!-- right edge: − (inner) trims it, + (outer) grows it -->
                            <span class="popup__btn-pair">
                                <button @click="handleReduceRight" class="popup__btn" :disabled="!canReduce"
                                    :title="$t('reduce_mention_right')" :aria-label="$t('reduce_mention_right')">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="m15 18-6-6 6-6" />
                                    </svg>
                                </button>
                                <button @click="handleExtendRight" class="popup__btn" :disabled="!canExtendRight"
                                    :title="$t('extend_mention_right')" :aria-label="$t('extend_mention_right')">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="m9 18 6-6-6-6" />
                                    </svg>
                                </button>
                            </span>
                            <button @click="handleRemoveMention" class="popup__btn"
                                :title="$t('remove_mention')" :aria-label="$t('remove_mention')">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M18 6 6 18" />
                                    <path d="m6 6 12 12" />
                                </svg>
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
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
                                    <circle cx="7.5" cy="7.5" r="1" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    <p class="popup__empty">{{ $t("no_mention") }}</p>
                </div>
            </template>
        </div>
    </Teleport>
</template>
