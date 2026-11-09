<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import EntityAddForm from "./entity_add_form.vue";
import EntityDeleteConfirmation from "./entity_delete_confirmation.vue";
import EntityEditForm from "./entity_edit_form.vue";
import EntityRegisterRow from "./entity_register_row.vue";
import EntityTypeFilter from "./entity_type_filter.vue";
import { useTranscriptStore } from "./transcript_store";
import { useViewSettingsStore } from "./view_settings_store";

const emit = defineEmits<{
    jump: [segmentIndex: number];
}>();

const store = useTranscriptStore();
const { entities } = storeToRefs(store);
const view = useViewSettingsStore();

// The ids of the rows that show their mentions.
const expandedIds = ref(new Set<string>());

function setExpanded(entityId: string, open: boolean) {
    if (open) {
        expandedIds.value.add(entityId);
    } else {
        expandedIds.value.delete(entityId);
    }
}

// The type filter hides rows, the highlighting toggle does not.
const rows = computed(() =>
    Object.entries(entities.value)
        .filter(([, entity]) => view.visibleEntityTypes.includes(entity.type))
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
        <EntityTypeFilter />

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
        <p v-else-if="Object.keys(entities).length > 0" class="u-color-muted">
            {{ $t("entity_register_filtered_empty") }}
        </p>
        <p v-else class="u-color-muted">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
