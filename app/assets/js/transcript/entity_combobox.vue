<script setup lang="ts">
import { computed, ref } from "vue";

import CheckIcon from "../icons/check_icon.vue";
import { entityMeta } from "./entities";
import type { Entity } from "./types";

const props = withDefaults(
    defineProps<{
        // The initial text of the name input.
        proposedName: string;
        entities: Record<string, Entity>;
        // The document's language, for sorting by name.
        language?: string | null;
        // The entity the mention is linked to, selected when the combobox
        // opens.
        entityId?: string | null;
    }>(),
    { language: null, entityId: null },
);

const emit = defineEmits<{
    select: [entityId: string];
    create: [name: string];
    cancel: [];
}>();

const sortedEntities = computed(() =>
    Object.entries(props.entities)
        .map(([id, entity]) => ({ id, entity }))
        .sort((a, b) =>
            a.entity.name.localeCompare(
                b.entity.name,
                props.language ?? undefined,
            ),
        ),
);

// The id of the entity chosen in the select, or "" for none.
const selectedId = ref(props.entityId ?? "");

const name = ref(props.proposedName);

// The trimmed name, or null when creating it would violate invariant 4.
const createName = computed(() => {
    const trimmed = name.value.trim();
    if (trimmed === "") return null;
    const taken = Object.values(props.entities).some(
        (entity) => entity.name === trimmed,
    );
    return taken ? null : trimmed;
});

function link() {
    if (selectedId.value !== "") emit("select", selectedId.value);
}

function create() {
    if (createName.value !== null) emit("create", createName.value);
}

function handleInputKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
        event.preventDefault();
        create();
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
        <div v-if="sortedEntities.length > 0" class="entity-combobox__pick">
            <select
                v-model="selectedId"
                class="entity-combobox__select"
                :aria-label="$t('entity_section')"
            >
                <option value="">{{ $t("entity_none") }}</option>
                <option
                    v-for="entry in sortedEntities"
                    :key="entry.id"
                    :value="entry.id"
                    class="entity-combobox__option"
                >
                    <span
                        class="entity-combobox__swatch"
                        :style="swatchStyle(entry.entity.type)"
                    ></span>
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
        <div class="entity-combobox__new">
            <input
                v-model="name"
                class="entity-combobox__input"
                type="text"
                :aria-label="$t('entity_new_name')"
                :placeholder="$t('entity_new_name')"
                @keydown="handleInputKeydown"
            />
            <button
                v-if="createName !== null"
                type="button"
                class="entity-combobox__create"
                @click="create"
            >
                {{ $t("entity_create", { name: createName }) }}
            </button>
        </div>
    </div>
</template>
