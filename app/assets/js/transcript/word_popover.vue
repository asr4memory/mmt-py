<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { computed, onBeforeUnmount, onMounted, ref, toRef } from "vue";
import { entityMeta } from "./entities";
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

const entityText = computed(() =>
    store.mentionText(props.segmentIndex, props.word.mentionId),
);

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

            <!-- structure toolbar: insert-left · insert-right · delete -->
            <div class="toolbar" role="toolbar" aria-label="Structure">
                <button @click="handleLeftInsert" class="tool-btn" :title="$t('add_word_left')"
                    :aria-label="$t('add_word_left')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                        stroke-linecap="round" stroke-linejoin="round">
                        <line x1="4" y1="4" x2="4" y2="20" />
                        <line x1="9.5" y1="12" x2="19" y2="12" />
                        <line x1="14.25" y1="7.5" x2="14.25" y2="16.5" />
                    </svg>
                </button>
                <button @click="handleRightInsert" class="tool-btn" :title="$t('add_word_right')"
                    :aria-label="$t('add_word_right')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                        stroke-linecap="round" stroke-linejoin="round">
                        <line x1="20" y1="4" x2="20" y2="20" />
                        <line x1="5" y1="12" x2="14.5" y2="12" />
                        <line x1="9.75" y1="7.5" x2="9.75" y2="16.5" />
                    </svg>
                </button>
                <span class="toolbar__spacer"></span>
                <button @click="handleRemove" class="tool-btn tool-btn--danger" :title="$t('remove_word')"
                    :aria-label="$t('remove_word')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                        stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 7h14" />
                        <path d="M9 7V5h6v2" />
                        <path d="M7.3 7l1 13h7.4l1-13" />
                    </svg>
                </button>
            </div>

            <!-- word -->
            <div class="word-head">
                <span class="word-head__word">{{ word.word }}</span>
            </div>

            <!-- info rows -->
            <div class="info">
                <div class="info__row">
                    <span class="info__label">{{ $t("timestamps") }}</span>
                    <span class="info__val">
                        <TimecodeRange :start="word.start" :end="word.end" />
                    </span>
                </div>
                <div class="info__row">
                    <span class="info__label">{{ $t("confidence") }}</span>
                    <span class="conf">
                        <meter class="conf__meter" :value="word.score" min="0" max="1"></meter>
                        <span class="conf__num">{{ formattedScore }}</span>
                    </span>
                </div>
            </div>

            <!-- entity section: only when the word is part of a mention -->
            <template v-if="mention">
                <div class="divider"></div>
                <div class="entity-head">{{ entityText }}</div>
                <div class="info">
                    <div class="info__row">
                        <span class="info__label">{{ $t("entity_type") }}</span>
                        <span
                            class="pill pill--small"
                            :style="entityMetaInfo ? { '--pill-base': `var(${entityMetaInfo.colorVar})` } : {}"
                        >
                            {{ $t(entityMetaInfo?.nameKey ?? "") || mention.label }}
                        </span>
                    </div>
                    <div class="info__row">
                        <span class="info__label">{{ $t("entity_confidence") }}</span>
                        <span class="conf">
                            <meter class="conf__meter" :value="mention.score" min="0" max="1"></meter>
                            <span class="conf__num">{{ formattedEntityScore }}</span>
                        </span>
                    </div>
                </div>
            </template>

            <div class="divider"></div>
        </div>
    </Teleport>
</template>
