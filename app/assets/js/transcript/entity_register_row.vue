<script setup lang="ts">
import { computed } from "vue";

import { entityMeta } from "./entities";
import type { Entity } from "./types";

const props = defineProps<{
    entity: Entity;
    mentionCount: number;
}>();

const swatchStyle = computed(() => {
    const meta = entityMeta(props.entity.type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
});

const typeName = computed(
    () => entityMeta(props.entity.type)?.nameKey ?? props.entity.type,
);

const aliases = computed(() => props.entity.aliases.join(", "));

// The full text of the name line, which the ellipsis may cut off.
const title = computed(() =>
    [props.entity.name, aliases.value].filter(Boolean).join(" "),
);

const wikidataUrl = computed(() =>
    props.entity.wikidataId
        ? `https://www.wikidata.org/wiki/${props.entity.wikidataId}`
        : null,
);
</script>

<template>
    <li class="entity-register-row">
        <span class="entity-register-row__swatch" :style="swatchStyle"></span>
        <p class="entity-register-row__names" :title="title">
            <span class="entity-register-row__name">{{ entity.name }}</span>
            <span v-if="aliases" class="entity-register-row__aliases">{{
                aliases
            }}</span>
        </p>
        <p class="entity-register-row__details">
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
