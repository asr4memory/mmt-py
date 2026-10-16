<script setup lang="ts">
import { computed } from "vue";

import PencilIcon from "../icons/pencil_icon.vue";
import TrashIcon from "../icons/trash_icon.vue";
import { entityMeta } from "./entities";
import type { Entity } from "./types";

const props = defineProps<{
    entity: Entity;
    mentionCount: number;
}>();

const emit = defineEmits<{
    edit: [];
    delete: [];
}>();

const swatchStyle = computed(() => {
    const meta = entityMeta(props.entity.type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
});

const typeName = computed(
    () => entityMeta(props.entity.type)?.nameKey ?? props.entity.type,
);

const wikidataUrl = computed(() =>
    props.entity.wikidataId
        ? `https://www.wikidata.org/wiki/${props.entity.wikidataId}`
        : null,
);
</script>

<template>
    <li class="entity-register-row">
        <div class="entity-register-row__head">
            <!-- The title holds the full name, which the ellipsis may cut off. -->
            <p class="entity-register-row__names" :title="entity.name">
                <span class="entity-register-row__name">{{ entity.name }}</span>
            </p>
            <button
                type="button"
                class="icon-button entity-register-row__edit"
                :title="$t('entity_edit')"
                :aria-label="$t('entity_edit')"
                @click="emit('edit')"
            >
                <PencilIcon class="icon-button__icon" />
            </button>
            <button
                type="button"
                class="icon-button entity-register-row__delete"
                :title="$t('entity_delete')"
                :aria-label="$t('entity_delete')"
                @click="emit('delete')"
            >
                <TrashIcon class="icon-button__icon" />
            </button>
        </div>
        <p class="entity-register-row__details">
            <span class="entity-register-row__swatch" :style="swatchStyle"></span>
            <span class="entity-register-row__type">{{ $t(typeName) }}</span>
            ·
            <span
                class="entity-register-row__count"
                :title="$t('entity_mention_count', mentionCount)"
                :aria-label="$t('entity_mention_count', mentionCount)"
                >{{
                    $t("entity_mention_count_short", { count: mentionCount })
                }}</span
            >
            <template v-if="wikidataUrl">
                ·
                <a :href="wikidataUrl" target="_blank" rel="noopener">{{
                    entity.wikidataId
                }}</a>
            </template>
        </p>
    </li>
</template>
