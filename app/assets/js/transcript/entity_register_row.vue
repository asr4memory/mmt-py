<script setup lang="ts">
import { computed } from "vue";

import PencilIcon from "../icons/pencil_icon.vue";
import TrashIcon from "../icons/trash_icon.vue";
import formatClockTime from "../shared/format_clock_time";
import { entityMeta } from "./entities";
import type { Entity, MentionRef } from "./types";

const props = defineProps<{
    entity: Entity;
    mentionCount: number;
    // The entity's mentions while the row is expanded, null while it is
    // collapsed.
    mentions: MentionRef[] | null;
}>();

const emit = defineEmits<{
    edit: [];
    delete: [];
    toggle: [open: boolean];
    jump: [segmentIndex: number];
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
            <template v-if="wikidataUrl">
                ·
                <a :href="wikidataUrl" target="_blank" rel="noopener">{{
                    entity.wikidataId
                }}</a>
            </template>
        </p>
        <details
            v-if="mentionCount > 0"
            class="entity-register-row__expand"
            :open="mentions !== null"
            @toggle="
                emit('toggle', ($event.target as HTMLDetailsElement).open)
            "
        >
            <summary class="entity-register-row__count entity-register-row__summary">
                {{ $t("entity_mention_count", mentionCount) }}
            </summary>
            <ul v-if="mentions !== null" class="entity-register-row__mentions">
                <li v-for="mention in mentions" :key="mention.mentionId">
                    <button
                        type="button"
                        class="entity-register-row__mention"
                        @click="emit('jump', mention.segmentIndex)"
                    >
                        <span class="entity-register-row__time">{{ formatClockTime(mention.start) }}</span>{{ " " }}<template v-if="mention.before">{{ mention.before }}{{ " " }}</template><mark class="entity-register-row__surface">{{ mention.surface }}</mark><template v-if="mention.after">{{ " " }}{{ mention.after }}</template>
                    </button>
                </li>
            </ul>
        </details>
        <p v-else class="entity-register-row__count">
            {{ $t("entity_mention_count", mentionCount) }}
        </p>
    </li>
</template>
