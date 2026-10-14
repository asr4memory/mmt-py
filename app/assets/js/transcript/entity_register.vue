<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import EntityRegisterRow from "./entity_register_row.vue";
import { useTranscriptStore } from "./transcript_store";

const store = useTranscriptStore();
const { entities } = storeToRefs(store);

const rows = computed(() =>
    Object.entries(entities.value)
        .map(([id, entity]) => ({
            id,
            entity,
            mentionCount: store.mentionCount(id),
        }))
        .sort((a, b) => a.entity.name.localeCompare(b.entity.name)),
);
</script>

<template>
    <section class="entity-register">
        <h3 class="u-mt-none">{{ $t("entities") }}</h3>
        <ul v-if="rows.length > 0" class="entity-register__list">
            <EntityRegisterRow
                v-for="row in rows"
                :key="row.id"
                :entity="row.entity"
                :mention-count="row.mentionCount"
            />
        </ul>
        <p v-else class="entity-register__empty">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
