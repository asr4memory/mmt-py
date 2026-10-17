<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import EntityAddForm from "./entity_add_form.vue";
import EntityDeleteConfirmation from "./entity_delete_confirmation.vue";
import EntityEditForm from "./entity_edit_form.vue";
import EntityRegisterRow from "./entity_register_row.vue";
import { useTranscriptStore } from "./transcript_store";

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

// Adding (UC-15), in the form above the list.
const adding = ref(false);

// Editing (UC-6), in the form that replaces the row.
const editingId = ref<string | null>(null);

function startEdit(entityId: string) {
    editingId.value = entityId;
    deletingId.value = null;
}

// Deleting (UC-7), confirmed in place of the row.
const deletingId = ref<string | null>(null);

function startDelete(entityId: string) {
    deletingId.value = entityId;
    editingId.value = null;
}
</script>

<template>
    <section class="entity-register">
        <h3 class="u-mt-none">{{ $t("entities") }}</h3>

        <button
            v-if="!adding"
            type="button"
            class="entity-register__add-toggle"
            @click="adding = true"
        >
            + {{ $t("entity_add") }}
        </button>
        <EntityAddForm v-else @close="adding = false" />

        <ul v-if="rows.length > 0" class="u-list-plain">
            <template v-for="row in rows" :key="row.id">
                <EntityEditForm
                    v-if="editingId === row.id"
                    :entity-id="row.id"
                    @close="editingId = null"
                />
                <EntityDeleteConfirmation
                    v-else-if="deletingId === row.id"
                    :entity-id="row.id"
                    @close="deletingId = null"
                />
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
        <p v-else class="u-color-muted">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
