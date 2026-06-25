<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { useTranscriptStore } from "./transcript_store";

const props = defineProps<{
    label: string;
    uploadedFileId: number;
    duration?: string;
    language?: string;
    source?: string;
}>();

defineEmits<{ save: []; discard: [] }>();

const store = useTranscriptStore();
const { dirtySegmentCount, transcriptIsDirty } = storeToRefs(store);

const saveStatusClass = computed(() =>
    transcriptIsDirty.value ? "save-status--unsaved" : "save-status--saved",
);

const shortLabel = computed(() => {
    const dotIndex = props.label.lastIndexOf(".");
    if (dotIndex <= 0) return props.label;
    const stem = props.label.slice(0, dotIndex);
    const ext = props.label.slice(dotIndex + 1);
    if (stem.length <= 20) return props.label;
    return `${stem.slice(0, 20)}...${ext}`;
});

const uploadedFileURL = computed(
    () => `/uploaded-files/${props.uploadedFileId}/`,
);
</script>

<template>
    <div class="transcript-subhead">
        <dl class="file-meta">
            <div class="file-meta__item">
                <span class="file-meta__label">{{ $t("file") }}</span> ·
                <a :href="uploadedFileURL">{{ shortLabel }}</a>
            </div>
            <div v-if="duration" class="file-meta__item">
                <span class="file-meta__label">{{ $t("duration") }}</span> ·
                {{ duration }}
            </div>
            <div v-if="language" class="file-meta__item">
                <span class="file-meta__label">{{ $t("language") }}</span> ·
                {{ language }}
            </div>
            <div v-if="source" class="file-meta__item">
                <span class="file-meta__label">{{ $t("source") }}</span> ·
                {{ source }}
            </div>
        </dl>

        <div class="transcript-actions">
            <span class="save-status" :class="saveStatusClass">
                <span class="save-status__dot"></span>
                <template v-if="transcriptIsDirty">
                    {{
                        $t(
                            "changed_segments",
                            { count: dirtySegmentCount },
                            dirtySegmentCount,
                        )
                    }}
                    · {{ $t("unsaved") }}
                </template>
                <template v-else>{{ $t("no_changes") }}</template>
            </span>
            <button
                type="button"
                class="btn btn--ghost"
                :disabled="!transcriptIsDirty"
                @click="$emit('discard')"
            >
                {{ $t("discard") }}
            </button>
            <button
                type="button"
                class="btn btn--primary"
                :disabled="!transcriptIsDirty"
                @click="$emit('save')"
            >
                {{ $t("save_transcript") }}
            </button>
        </div>
    </div>
</template>
