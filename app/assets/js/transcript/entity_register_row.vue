<script setup lang="ts">
import { computed, ref } from "vue";

import CheckIcon from "../icons/check_icon.vue";
import CloseIcon from "../icons/close_icon.vue";
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

// True while the row asks to confirm the deletion.
const confirmingDelete = ref(false);

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
        <template v-if="confirmingDelete">
            <p class="entity-register-row__names">
                <i>{{ entity.name }}</i>{{ $t("entity_delete_confirm") }}
            </p>
            <div class="entity-register-row__actions">
                <button
                    type="button"
                    class="icon-button icon-button--danger entity-register-row__delete-confirm"
                    :title="$t('entity_delete')"
                    @click="emit('delete')"
                >
                    <CheckIcon class="icon-button__icon" />
                </button>
                <button
                    type="button"
                    class="icon-button entity-register-row__action entity-register-row__delete-cancel"
                    :title="$t('cancel')"
                    @click="confirmingDelete = false"
                >
                    <CloseIcon class="icon-button__icon" />
                </button>
            </div>
        </template>
        <template v-else>
            <p class="entity-register-row__names" :title="title">
                <span class="entity-register-row__name">{{ entity.name }}</span>
                <span v-if="aliases" class="entity-register-row__aliases">{{
                    aliases
                }}</span>
            </p>
            <div class="entity-register-row__actions">
                <button
                    type="button"
                    class="icon-button entity-register-row__action entity-register-row__edit"
                    :title="$t('entity_edit')"
                    @click="emit('edit')"
                >
                    <PencilIcon class="icon-button__icon" />
                </button>
                <button
                    type="button"
                    class="icon-button entity-register-row__action entity-register-row__delete"
                    :title="$t('entity_delete')"
                    @click="confirmingDelete = true"
                >
                    <TrashIcon class="icon-button__icon" />
                </button>
            </div>
        </template>
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
