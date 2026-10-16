<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, useTemplateRef } from "vue";

import { entityMeta, LINKABLE_TYPES } from "./entities";
import EntityEditForm from "./entity_edit_form.vue";
import { entityProblems, normalizedSurface } from "./entity_matching";
import EntityRegisterRow from "./entity_register_row.vue";
import { useTranscriptStore } from "./transcript_store";
import type { EntityType } from "./types";

// The search field is shown once the register holds more entities than this.
const SEARCH_THRESHOLD = 8;

const store = useTranscriptStore();
const { entities } = storeToRefs(store);

const searchVisible = computed(
    () => Object.keys(entities.value).length > SEARCH_THRESHOLD,
);
const search = ref("");

function matchesSearch(names: string[]): boolean {
    const query = normalizedSurface(search.value);
    if (!searchVisible.value || query === "") return true;
    return names.some((name) => normalizedSurface(name).includes(query));
}

const rows = computed(() =>
    Object.entries(entities.value)
        .filter(([, entity]) => matchesSearch([entity.name, ...entity.aliases]))
        .map(([id, entity]) => ({
            id,
            entity,
            mentionCount: store.mentionCount(id),
        }))
        .sort((a, b) => a.entity.name.localeCompare(b.entity.name)),
);

const addFormOpen = ref(false);
const newName = ref("");
const newType = ref<EntityType>("PER");
const addInput = useTemplateRef<HTMLInputElement>("addInput");

const addProblems = computed(() =>
    entityProblems(
        { name: newName.value, aliases: [], wikidataId: null },
        entities.value,
        null,
    ),
);

const canAdd = computed(
    () => !addProblems.value.emptyName && !addProblems.value.nameTaken,
);

function openAddForm() {
    newName.value = "";
    newType.value = "PER";
    addFormOpen.value = true;
    nextTick(() => addInput.value?.focus());
}

function confirmAdd() {
    if (!canAdd.value) return;
    store.createEntity(newName.value, newType.value);
    addFormOpen.value = false;
}

// The entity whose row is shown as the edit form, one at a time.
const editingId = ref<string | null>(null);
</script>

<template>
    <section class="entity-register">
        <h3 class="u-mt-none">{{ $t("entities") }}</h3>
        <button
            v-if="!addFormOpen"
            type="button"
            class="entity-register__text-button entity-register__add-toggle"
            @click="openAddForm"
        >
            + {{ $t("entity_add") }}
        </button>
        <div
            v-else
            class="entity-register__add-form"
            @keydown.esc="addFormOpen = false"
        >
            <input
                ref="addInput"
                v-model="newName"
                type="text"
                class="form__input entity-register__add-name"
                :placeholder="$t('entity_name')"
                :aria-label="$t('entity_name')"
                :aria-invalid="addProblems.nameTaken"
                @keydown.enter.prevent="confirmAdd"
            />
            <p v-if="addProblems.nameTaken" class="form__error">
                {{ $t("entity_name_taken") }}
            </p>
            <select
                v-model="newType"
                class="entity-register__add-type"
                :aria-label="$t('entity_type')"
            >
                <option v-for="type in LINKABLE_TYPES" :key="type" :value="type">
                    {{ $t(entityMeta(type)?.nameKey ?? type) }}
                </option>
            </select>
            <div class="entity-register__add-actions">
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
                    class="button button--secondary button--small"
                    @click="addFormOpen = false"
                >
                    {{ $t("cancel") }}
                </button>
            </div>
        </div>
        <input
            v-if="searchVisible"
            v-model="search"
            type="search"
            class="form__input entity-register__search"
            :placeholder="$t('entity_search')"
            :aria-label="$t('entity_search')"
        />
        <ul v-if="rows.length > 0" class="entity-register__list">
            <template v-for="row in rows" :key="row.id">
                <EntityEditForm
                    v-if="editingId === row.id"
                    :entity-id="row.id"
                    @close="editingId = null"
                />
                <EntityRegisterRow
                    v-else
                    :entity="row.entity"
                    :mention-count="row.mentionCount"
                    @edit="editingId = row.id"
                    @delete="store.deleteEntity(row.id)"
                />
            </template>
        </ul>
        <p v-else-if="!searchVisible" class="entity-register__empty">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
