<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import CheckIcon from "../icons/check_icon.vue";
import CloseIcon from "../icons/close_icon.vue";
import { entityMeta, LINKABLE_TYPES } from "./entities";
import EntityRegisterRow from "./entity_register_row.vue";
import { useTranscriptStore } from "./transcript_store";
import type { EntityType } from "./types";

const WIKIDATA_ID = /^Q[1-9][0-9]*$/;

const emit = defineEmits<{
    jump: [segmentIndex: number];
}>();

const store = useTranscriptStore();
const { entities } = storeToRefs(store);

// The ids of the rows that show their mentions.
const expandedIds = ref(new Set<string>());

function setExpanded(entityId: string, open: boolean) {
    if (open) {
        expandedIds.value.add(entityId);
    } else {
        expandedIds.value.delete(entityId);
    }
}

const rows = computed(() =>
    Object.entries(entities.value)
        .map(([id, entity]) => ({
            id,
            entity,
            mentionCount: store.mentionCount(id),
        }))
        .sort((a, b) => a.entity.name.localeCompare(b.entity.name)),
);

// Whether an entity other than exceptId has the name. Names are compared
// exactly (invariant 4).
function nameTaken(name: string, exceptId: string | null) {
    return Object.entries(entities.value).some(
        ([id, entity]) => id !== exceptId && entity.name === name,
    );
}

// Whether an entity other than exceptId has the Wikidata ID (invariant 5).
function wikidataTaken(wikidataId: string, exceptId: string) {
    return Object.entries(entities.value).some(
        ([id, entity]) => id !== exceptId && entity.wikidataId === wikidataId,
    );
}

function typeName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}

// Adding (UC-15).
const adding = ref(false);
const addName = ref("");
const addType = ref<EntityType>("PER");

const addNameTaken = computed(() => nameTaken(addName.value.trim(), null));
const canAdd = computed(
    () => addName.value.trim() !== "" && !addNameTaken.value,
);

function openAddForm() {
    addName.value = "";
    addType.value = "PER";
    adding.value = true;
}

function confirmAdd() {
    if (!canAdd.value) return;
    store.createEntity(addName.value, addType.value);
    adding.value = false;
}

// Editing (UC-6). The type is shown but cannot be changed.
const editingId = ref<string | null>(null);
const editName = ref("");
const editWikidataId = ref("");

const editNameTaken = computed(() =>
    nameTaken(editName.value.trim(), editingId.value),
);
const trimmedWikidataId = computed(() => editWikidataId.value.trim());
// An empty field is valid and means no identifier.
const wikidataMalformed = computed(
    () =>
        trimmedWikidataId.value !== "" &&
        !WIKIDATA_ID.test(trimmedWikidataId.value),
);
const editWikidataTaken = computed(
    () =>
        editingId.value !== null &&
        trimmedWikidataId.value !== "" &&
        wikidataTaken(trimmedWikidataId.value, editingId.value),
);
const canSaveEdit = computed(
    () =>
        editName.value.trim() !== "" &&
        !editNameTaken.value &&
        !wikidataMalformed.value &&
        !editWikidataTaken.value,
);

function startEdit(entityId: string) {
    const entity = entities.value[entityId];
    editingId.value = entityId;
    editName.value = entity.name;
    editWikidataId.value = entity.wikidataId ?? "";
    deletingId.value = null;
}

function confirmEdit() {
    if (!canSaveEdit.value || editingId.value === null) return;
    store.updateEntity(
        editingId.value,
        editName.value.trim(),
        trimmedWikidataId.value === "" ? null : trimmedWikidataId.value,
    );
    editingId.value = null;
}

// Deleting (UC-7), confirmed in place.
const deletingId = ref<string | null>(null);

function startDelete(entityId: string) {
    deletingId.value = entityId;
    editingId.value = null;
}

function confirmDelete() {
    if (deletingId.value === null) return;
    store.deleteEntity(deletingId.value);
    deletingId.value = null;
}
</script>

<template>
    <section class="entity-register">
        <h3 class="u-mt-none">{{ $t("entities") }}</h3>

        <button
            v-if="!adding"
            type="button"
            class="entity-register__add-toggle"
            @click="openAddForm"
        >
            + {{ $t("entity_add") }}
        </button>
        <div v-else class="entity-register__add-form entity-register__form">
            <input
                v-model="addName"
                type="text"
                class="entity-register__add-name"
                :aria-label="$t('entity_name')"
                :placeholder="$t('entity_name')"
                @keyup.enter="confirmAdd"
                @keyup.esc="adding = false"
            />
            <p v-if="addNameTaken" class="entity-register__error">
                {{ $t("entity_name_taken") }}
            </p>
            <select
                v-model="addType"
                class="entity-register__add-type"
                :aria-label="$t('entity_type')"
            >
                <option v-for="type in LINKABLE_TYPES" :key="type" :value="type">
                    {{ $t(typeName(type)) }}
                </option>
            </select>
            <div class="entity-register__form-actions">
                <button
                    type="button"
                    class="button button--primary button--small entity-register__add-confirm"
                    :disabled="!canAdd"
                    @click="confirmAdd"
                >
                    {{ $t("add") }}
                </button>
                <button
                    type="button"
                    class="button button--secondary button--small entity-register__add-cancel"
                    @click="adding = false"
                >
                    {{ $t("cancel") }}
                </button>
            </div>
        </div>

        <ul v-if="rows.length > 0" class="entity-register__list">
            <template v-for="row in rows" :key="row.id">
                <li
                    v-if="editingId === row.id"
                    class="entity-register-row entity-register__edit-form entity-register__form"
                >
                    <input
                        v-model="editName"
                        type="text"
                        class="entity-register__edit-name"
                        :aria-label="$t('entity_name')"
                        @keyup.enter="confirmEdit"
                        @keyup.esc="editingId = null"
                    />
                    <p v-if="editNameTaken" class="entity-register__error">
                        {{ $t("entity_name_taken") }}
                    </p>
                    <p class="entity-register__type">
                        {{ $t("entity_type") }}: {{ $t(typeName(row.entity.type)) }}
                    </p>
                    <input
                        v-model="editWikidataId"
                        type="text"
                        class="entity-register__edit-wikidata"
                        :aria-label="$t('entity_wikidata_id')"
                        :aria-invalid="wikidataMalformed ? 'true' : 'false'"
                        :placeholder="$t('entity_wikidata_id')"
                        @keyup.enter="confirmEdit"
                        @keyup.esc="editingId = null"
                    />
                    <p v-if="editWikidataTaken" class="entity-register__error">
                        {{ $t("entity_wikidata_taken") }}
                    </p>
                    <div class="entity-register__form-actions">
                        <button
                            type="button"
                            class="button button--primary button--small entity-register__edit-confirm"
                            :disabled="!canSaveEdit"
                            @click="confirmEdit"
                        >
                            {{ $t("save") }}
                        </button>
                        <button
                            type="button"
                            class="button button--secondary button--small entity-register__edit-cancel"
                            @click="editingId = null"
                        >
                            {{ $t("cancel") }}
                        </button>
                    </div>
                </li>
                <li
                    v-else-if="deletingId === row.id"
                    class="entity-register-row entity-register__delete"
                >
                    <span class="entity-register__delete-question">
                        <i>{{ row.entity.name }}</i
                        >{{ $t("entity_delete_confirm") }}
                    </span>
                    <button
                        type="button"
                        class="icon-button icon-button--danger entity-register__delete-confirm"
                        :title="$t('entity_delete')"
                        :aria-label="$t('entity_delete')"
                        @click="confirmDelete"
                    >
                        <CheckIcon class="icon-button__icon" />
                    </button>
                    <button
                        type="button"
                        class="icon-button entity-register__delete-cancel"
                        :title="$t('cancel')"
                        :aria-label="$t('cancel')"
                        @click="deletingId = null"
                    >
                        <CloseIcon class="icon-button__icon" />
                    </button>
                </li>
                <EntityRegisterRow
                    v-else
                    :entity="row.entity"
                    :mention-count="row.mentionCount"
                    :mentions="
                        expandedIds.has(row.id)
                            ? store.mentionsOfEntity(row.id)
                            : null
                    "
                    @toggle="setExpanded(row.id, $event)"
                    @jump="emit('jump', $event)"
                    @edit="startEdit(row.id)"
                    @delete="startDelete(row.id)"
                />
            </template>
        </ul>
        <p v-else class="entity-register__empty">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
