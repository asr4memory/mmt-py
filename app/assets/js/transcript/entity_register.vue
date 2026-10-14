<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { entityMeta } from "./entities";
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

function swatchStyle(type: string) {
    const meta = entityMeta(type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
}

function typeName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}
</script>

<template>
    <section class="entity-register">
        <h3 class="u-mt-none">{{ $t("entities") }}</h3>
        <ul v-if="rows.length > 0" class="entity-register__list">
            <li v-for="row in rows" :key="row.id" class="entity-register__row">
                <span
                    class="entity-register__swatch"
                    :style="swatchStyle(row.entity.type)"
                ></span>
                <span class="entity-register__name">{{ row.entity.name }}</span>
                <span class="entity-register__type">{{
                    $t(typeName(row.entity.type))
                }}</span>
                <span class="entity-register__count">{{
                    $t("entity_mention_count", row.mentionCount)
                }}</span>
            </li>
        </ul>
        <p v-else class="entity-register__empty">
            {{ $t("entity_register_empty") }}
        </p>
    </section>
</template>
