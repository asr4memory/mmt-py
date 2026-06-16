<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, useTemplateRef, watch } from "vue";

import { useTranscriptStore } from "./transcript_store";

defineProps<{
    showConfidence: boolean;
    showEntities: boolean;
    showEdits: boolean;
    autoScroll: boolean;
}>();

defineEmits<{
    "update:showConfidence": [value: boolean];
    "update:showEntities": [value: boolean];
    "update:showEdits": [value: boolean];
    "update:autoScroll": [value: boolean];
}>();

const store = useTranscriptStore();
const { speakers } = storeToRefs(store);

const showAddForm = ref(false);
const newSpeakerName = ref("");
const addInput = useTemplateRef<HTMLInputElement>("addInput");

const editingName = ref<string | null>(null);
const editValue = ref("");
const editInput = useTemplateRef<HTMLInputElement>("editInput");

watch(showAddForm, (val) => {
    if (val) nextTick(() => addInput.value?.focus());
});

watch(editingName, (val) => {
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
            (s) => s.name !== editingName.value && s.name === trimmed,
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

function startEdit(name: string) {
    editingName.value = name;
    editValue.value = name;
}

function cancelEdit() {
    editingName.value = null;
}

function confirmEdit() {
    if (!canSaveEdit.value || editingName.value === null) return;
    store.renameSpeaker(editingName.value, editValue.value);
    editingName.value = null;
}
</script>

<template>
    <section>
        <h3 class="u-mt-none">{{ $t("view") }}</h3>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showConfidence"
                @change="
                    $emit(
                        'update:showConfidence',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_confidence") }}</span>
        </label>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showEntities"
                @change="
                    $emit(
                        'update:showEntities',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_entities") }}</span>
        </label>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showEdits"
                @change="
                    $emit(
                        'update:showEdits',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_edits") }}</span>
        </label>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="autoScroll"
                @change="
                    $emit(
                        'update:autoScroll',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("auto_scroll") }}</span>
        </label>
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("speakers") }}</h3>
        <ul class="speaker-legend u-mt-none u-mb-none">
            <li
                v-for="speaker in speakers"
                :key="speaker.name"
                class="speaker-legend__item"
            >
                <span
                    class="speaker-legend__swatch"
                    :style="{ backgroundColor: speaker.color }"
                ></span>
                <template v-if="editingName === speaker.name">
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
                <template v-else>
                    <span class="speaker-legend__name">{{ speaker.name }}</span>
                    <button
                        class="speaker-legend__edit-toggle"
                        :title="$t('edit_speaker')"
                        @click="startEdit(speaker.name)"
                    >
                        ✎
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
                <button :disabled="!canAdd" @click="confirmAdd">
                    {{ $t("add") }}
                </button>
                <button @click="cancelAdd">{{ $t("cancel") }}</button>
            </div>
        </div>
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("named_entities") }}</h3>
        <ul class="entity-legend-list u-mt-none u-mb-none">
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--per"
                ></span>
                {{ $t("entity_per") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--loc"
                ></span>
                {{ $t("entity_loc") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--org"
                ></span>
                {{ $t("entity_org") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--date"
                ></span>
                {{ $t("entity_date") }}
            </li>
        </ul>
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("shortcuts") }}</h3>
        <div class="shortcuts">
            <div class="shortcut">
                <span class="shortcut__label">{{
                    $t("shortcut_play_pause")
                }}</span>
                <span
                    ><kbd class="kbd">Space</kbd> / <kbd class="kbd">P</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_back") }}</span>
                <kbd class="kbd">←</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_forward") }}</span>
                <kbd class="kbd">→</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_volume") }}</span>
                <span
                    ><kbd class="kbd">⇧ ↑</kbd> / <kbd class="kbd">⇧ ↓</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_mute") }}</span>
                <kbd class="kbd">M</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_speed") }}</span>
                <span
                    ><kbd class="kbd">&lt;</kbd> / <kbd class="kbd">&gt;</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{
                    $t("shortcut_fullscreen")
                }}</span>
                <kbd class="kbd">F</kbd>
            </div>
        </div>
    </section>
</template>
