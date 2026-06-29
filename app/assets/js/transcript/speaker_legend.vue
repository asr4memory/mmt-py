<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, useTemplateRef, watch } from "vue";

import { useTranscriptStore } from "./transcript_store";

const store = useTranscriptStore();
const { speakers } = storeToRefs(store);

const showAddForm = ref(false);
const newSpeakerName = ref("");
const addInput = useTemplateRef<HTMLInputElement>("addInput");

const editingId = ref<string | null>(null);
const editValue = ref("");
const editInput = useTemplateRef<HTMLInputElement>("editInput");

const deletingId = ref<string | null>(null);

watch(showAddForm, (val) => {
    if (val) nextTick(() => addInput.value?.focus());
});

watch(editingId, (val) => {
    if (val !== null) nextTick(() => editInput.value?.focus());
});

const canAdd = computed(
    () =>
        newSpeakerName.value.trim() !== "" &&
        !speakers.value.some((s) => s.name === newSpeakerName.value.trim()),
);

const canSaveEdit = computed(() => {
    const trimmed = editValue.value.trim();
    return (
        trimmed !== "" &&
        !speakers.value.some(
            (s) => s.id !== editingId.value && s.name === trimmed,
        )
    );
});

function openAddForm() {
    newSpeakerName.value = "";
    showAddForm.value = true;
}

function cancelAdd() {
    showAddForm.value = false;
}

function confirmAdd() {
    if (!canAdd.value) return;
    store.addSpeaker(newSpeakerName.value);
    showAddForm.value = false;
}

function startEdit(speaker: { id: string; name: string }) {
    editingId.value = speaker.id;
    editValue.value = speaker.name;
}

function startDelete(speakerId: string) {
    deletingId.value = speakerId;
}

function cancelDelete() {
    deletingId.value = null;
}

function confirmDelete() {
    if (deletingId.value === null) return;
    store.deleteSpeaker(deletingId.value);
    deletingId.value = null;
}

function cancelEdit() {
    editingId.value = null;
}

function confirmEdit() {
    if (!canSaveEdit.value || editingId.value === null) return;
    store.renameSpeaker(editingId.value, editValue.value);
    editingId.value = null;
}
</script>

<template>
    <ul class="speaker-legend u-mt-none u-mb-none">
        <li
            v-for="speaker in speakers"
            :key="speaker.id"
            class="speaker-legend__item"
        >
            <span
                class="speaker-legend__swatch"
                :style="{ backgroundColor: speaker.color }"
            ></span>
            <template v-if="editingId === speaker.id">
                <input
                    type="text"
                    ref="editInput"
                    class="speaker-legend__edit-input"
                    v-model="editValue"
                    @keyup.enter="confirmEdit"
                    @keyup.esc="cancelEdit"
                    @blur="cancelEdit"
                />
                <button
                    class="speaker-legend__edit-action"
                    :disabled="!canSaveEdit"
                    @mousedown.prevent="confirmEdit"
                >
                    ✓
                </button>
                <button
                    class="speaker-legend__edit-action"
                    @mousedown.prevent="cancelEdit"
                >
                    &times;
                </button>
            </template>
            <template v-else-if="deletingId === speaker.id">
                <span class="speaker-legend__name">
                    <i>{{ speaker.name }}</i
                    >{{ $t("delete_speaker_confirm") }}
                </span>
                <button
                    class="speaker-legend__edit-action speaker-legend__delete-confirm"
                    :title="$t('delete_speaker')"
                    @mousedown.prevent="confirmDelete"
                >
                    ✓
                </button>
                <button
                    class="speaker-legend__edit-action speaker-legend__delete-cancel"
                    :title="$t('cancel')"
                    @mousedown.prevent="cancelDelete"
                >
                    &times;
                </button>
            </template>
            <template v-else>
                <span class="speaker-legend__name">{{ speaker.name }}</span>
                <button
                    class="speaker-legend__edit-toggle"
                    :title="$t('edit_speaker')"
                    @click="startEdit(speaker)"
                >
                    ✎
                </button>
                <button
                    class="speaker-legend__edit-toggle speaker-legend__delete-toggle"
                    :title="$t('delete_speaker')"
                    @click="startDelete(speaker.id)"
                >
                    🗑
                </button>
            </template>
        </li>
    </ul>
    <button
        v-if="!showAddForm"
        class="speaker-legend__add-toggle"
        @click="openAddForm"
    >
        + {{ $t("add_speaker") }}
    </button>
    <div v-else class="speaker-legend__add-form">
        <input
            type="text"
            ref="addInput"
            v-model="newSpeakerName"
            :placeholder="$t('speaker_name')"
            @keyup.enter="confirmAdd"
        />
        <div class="speaker-legend__add-actions">
            <button
                type="button"
                class="button button--primary button--small"
                :disabled="!canAdd"
                @click="confirmAdd"
            >
                {{ $t("add") }}
            </button>
            <button
                type="button"
                class="button button--secondary button--small"
                @click="cancelAdd"
            >
                {{ $t("cancel") }}
            </button>
        </div>
    </div>
</template>
