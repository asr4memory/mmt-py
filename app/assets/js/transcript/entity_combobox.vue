<script setup lang="ts">
import { computed, ref, watch } from "vue";

import CheckIcon from "../icons/check_icon.vue";
import { entityMeta } from "./entities";
import {
    entityNamed,
    normalizedSurface,
    rankEntities,
} from "./entity_matching";
import type { Entity } from "./types";

const props = withDefaults(
    defineProps<{
        // The initial text of the input.
        query: string;
        // The type that the rule A match requires.
        type: string;
        entities: Record<string, Entity>;
        // The document's language, for sorting by name.
        language?: string | null;
        // Whether a button below the input creates an entity named after the
        // query.
        creatable?: boolean;
        // The entity the mention is linked to, selected until the query
        // changes.
        entityId?: string | null;
    }>(),
    { language: null, creatable: true, entityId: null },
);

const emit = defineEmits<{
    select: [entityId: string];
    create: [name: string];
    cancel: [];
}>();

const text = ref(props.query);

const ranked = computed(() =>
    rankEntities(text.value, props.type, props.entities, props.language),
);

// The create button is left out when its entity would violate invariant 4.
const createName = computed(() => {
    if (!props.creatable) return null;
    const name = text.value.trim();
    if (normalizedSurface(name) === "") return null;
    if (entityNamed(name, props.entities) !== null) return null;
    return name;
});

// The id of the entity chosen in the select, or "" for none.
const selectedId = ref("");

// The given entity is selected first; every change of the query selects the
// rule A match, if there is one.
watch(
    text,
    (_text, previous) => {
        if (previous === undefined && props.entityId) {
            selectedId.value = props.entityId;
            return;
        }
        selectedId.value =
            ranked.value.find((entry) => entry.exactMatch)?.id ?? "";
    },
    { immediate: true },
);

function link() {
    if (selectedId.value !== "") emit("select", selectedId.value);
}

function handleInputKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
        event.preventDefault();
        link();
    }
}

function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
        // The popover closes on an Escape that reaches the document.
        event.stopPropagation();
        emit("cancel");
    }
}

function swatchStyle(type: string) {
    const meta = entityMeta(type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
}

function typeName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}
</script>

<template>
    <div class="entity-combobox" @keydown="handleKeydown">
        <input
            v-model="text"
            class="entity-combobox__input"
            type="text"
            :aria-label="$t('entity_search_or_create')"
            :placeholder="$t('entity_search_or_create')"
            @keydown="handleInputKeydown"
        />
        <button
            v-if="createName !== null"
            type="button"
            class="entity-combobox__create"
            @click="emit('create', createName)"
        >
            {{ $t("entity_create", { name: createName }) }}
        </button>
        <div v-if="ranked.length > 0" class="entity-combobox__pick">
            <select
                v-model="selectedId"
                class="entity-combobox__select"
                :aria-label="$t('entity_section')"
            >
                <option value="">{{ $t("entity_none") }}</option>
                <option
                    v-for="entry in ranked"
                    :key="entry.id"
                    :value="entry.id"
                    class="entity-combobox__option"
                >
                    <span
                        class="entity-combobox__swatch"
                        :style="swatchStyle(entry.entity.type)"
                    ></span>
                    <!-- One text node, so that a browser without base-select
                         shows the name and the type with a space between. -->
                    <span class="entity-combobox__name">{{
                        `${entry.entity.name} (${$t(typeName(entry.entity.type))})`
                    }}</span>
                </option>
            </select>
            <button
                type="button"
                class="popup__btn entity-combobox__link"
                :disabled="selectedId === ''"
                :title="$t('entity_link')"
                :aria-label="$t('entity_link')"
                @click="link"
            >
                <CheckIcon />
            </button>
        </div>
    </div>
</template>
