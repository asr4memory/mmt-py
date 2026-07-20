<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { routes } from "../shared/routes";
import { useTranscriptStore } from "./transcript_store";

const props = defineProps<{
    label: string;
    uploadedFileName: string;
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

const shortFileName = computed(() => {
    const dotIndex = props.uploadedFileName.lastIndexOf(".");
    if (dotIndex <= 0) return props.label;
    const stem = props.uploadedFileName.slice(0, dotIndex);
    const ext = props.uploadedFileName.slice(dotIndex + 1);
    if (stem.length <= 20) return props.uploadedFileName;
    return `${stem.slice(0, 20)}...${ext}`;
});

const uploadedFileURL = computed(() =>
    routes.uploadedFile(props.uploadedFileId),
);
</script>

<template>
    <div class="document-bar">
        <div class="container">
        <div class="document-bar__inner">
            <h1 class="u-mt-none u-mb-none">
                <b>{{ label }}</b>
            </h1>

            <a :href="uploadedFileURL">{{ shortFileName }}</a>

            <div class="document-bar__actions">
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
                    </template>
                    <template v-else>{{ $t("no_changes") }}</template>
                </span>
                <button
                    type="button"
                    class="button button--secondary button--small"
                    :disabled="!transcriptIsDirty"
                    @click="$emit('discard')"
                >
                    {{ $t("discard") }}
                </button>
                <button
                    type="button"
                    class="button button--primary button--small"
                    :disabled="!transcriptIsDirty"
                    @click="$emit('save')"
                >
                    {{ $t("save_transcript") }}
                </button>
            </div>
        </div>
        </div>
    </div>
</template>
