<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, useTemplateRef } from "vue";

import PencilIcon from "../icons/pencil_icon.vue";
import { routes } from "../shared/routes";
import { useTranscriptStore } from "./transcript_store";

const props = defineProps<{
    transcriptId: number;
    uploadedFileName: string;
    uploadedFileId: number;
    language?: string | null;
    source?: string;
    isSaving?: boolean;
}>();

defineEmits<{ save: []; discard: [] }>();

const store = useTranscriptStore();
const { label, transcriptIsDirty } = storeToRefs(store);

// The label is edited in place. Committing writes it to the store, which
// marks the transcript unsaved; the save button then writes it to the server
// together with the content.
const isRenaming = ref(false);
const draft = ref("");
const labelInput = useTemplateRef<HTMLInputElement>("labelInput");

async function startRenaming() {
    draft.value = label.value;
    isRenaming.value = true;
    await nextTick();
    labelInput.value?.focus();
    labelInput.value?.select();
}

function commitRename() {
    // The blur handler also runs when Escape has already closed the input.
    if (!isRenaming.value) return;
    isRenaming.value = false;

    const newLabel = draft.value.trim();
    if (newLabel === "") return;
    label.value = newLabel;
}

function cancelRename() {
    isRenaming.value = false;
}

const saveStatusClass = computed(() => {
    if (props.isSaving) return "save-status--saving";
    return transcriptIsDirty.value
        ? "save-status--unsaved"
        : "save-status--saved";
});

const shortFileName = computed(() => {
    const dotIndex = props.uploadedFileName.lastIndexOf(".");
    if (dotIndex <= 0) return props.uploadedFileName;
    const stem = props.uploadedFileName.slice(0, dotIndex);
    const ext = props.uploadedFileName.slice(dotIndex + 1);
    if (stem.length <= 20) return props.uploadedFileName;
    return `${stem.slice(0, 20)}...${ext}`;
});

const transcriptURL = computed(() => routes.transcript(props.transcriptId));

const uploadedFileURL = computed(() =>
    routes.uploadedFile(props.uploadedFileId),
);
</script>

<template>
    <div class="document-bar">
        <div class="container">
        <div class="document-bar__inner">
            <a :href="uploadedFileURL" class="document-bar__file-link" :aria-label="uploadedFileName"
                :title="uploadedFileName">{{ shortFileName }}</a>
            <span class="u-color-muted" aria-hidden="true">▸</span>
            <div>
                <h1 class="document-bar__title u-mt-none u-mb-none">
                    <input
                        v-if="isRenaming"
                        ref="labelInput"
                        v-model="draft"
                        class="document-bar__label-input"
                        type="text"
                        maxlength="255"
                        :aria-label="$t('transcript_label')"
                        @keydown.enter="commitRename"
                        @keyup.escape="cancelRename"
                        @blur="commitRename"
                    />
                    <a v-else :href="transcriptURL" class="document-bar__title-link">{{ label }}</a>
                </h1> <button
                    v-if="!isRenaming"
                    type="button"
                    class="icon-button document-bar__rename"
                    :title="$t('rename_transcript')"
                    :aria-label="$t('rename_transcript')"
                    @click="startRenaming"
                >
                    <PencilIcon class="icon-button__icon" />
                </button>
            </div>

            <div class="document-bar__actions">
                <span class="save-status" :class="saveStatusClass">
                    <template v-if="isSaving">{{ $t("saving") }}</template>
                    <template v-else-if="transcriptIsDirty">
                        {{ $t("unsaved_changes") }}
                    </template>
                    <template v-else>{{ $t("no_changes") }}</template>
                </span>
                <button
                    type="button"
                    class="button button--secondary button--small"
                    :disabled="isSaving || !transcriptIsDirty"
                    @click="$emit('discard')"
                >
                    {{ $t("discard") }}
                </button>
                <button
                    type="button"
                    class="button button--primary button--small"
                    :disabled="isSaving || !transcriptIsDirty"
                    @click="$emit('save')"
                >
                    {{ $t("save_transcript") }}
                </button>
            </div>
        </div>
        </div>
    </div>
</template>
