<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { entityMeta, LINKABLE_TYPES, nameTaken } from "./entities";
import { useTranscriptStore } from "./transcript_store";
import type { EntityType } from "./types";

const emit = defineEmits<{
    close: [];
}>();

const store = useTranscriptStore();
const { entities } = storeToRefs(store);

// Adding (UC-15).
const name = ref("");
const type = ref<EntityType>("PER");

const nameIsTaken = computed(() =>
    nameTaken(entities.value, name.value.trim(), null),
);
const canAdd = computed(() => name.value.trim() !== "" && !nameIsTaken.value);

function typeName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}

function confirm() {
    if (!canAdd.value) return;
    store.createEntity(name.value, type.value);
    emit("close");
}
</script>

<template>
    <div class="stack stack--tiny entity-form entity-add-form">
        <input
            v-model="name"
            type="text"
            class="entity-add-form__name"
            :aria-label="$t('entity_name')"
            :placeholder="$t('entity_name')"
            @keyup.enter="confirm"
            @keyup.esc="emit('close')"
        />
        <p v-if="nameIsTaken" class="entity-form__error">
            {{ $t("entity_name_taken") }}
        </p>
        <select
            v-model="type"
            class="entity-add-form__type"
            :aria-label="$t('entity_type')"
        >
            <option
                v-for="linkable in LINKABLE_TYPES"
                :key="linkable"
                :value="linkable"
            >
                {{ $t(typeName(linkable)) }}
            </option>
        </select>
        <div class="cluster cluster--tiny">
            <button
                type="button"
                class="button button--primary button--small entity-add-form__confirm"
                :disabled="!canAdd"
                @click="confirm"
            >
                {{ $t("add") }}
            </button>
            <button
                type="button"
                class="button button--secondary button--small entity-add-form__cancel"
                @click="emit('close')"
            >
                {{ $t("cancel") }}
            </button>
        </div>
    </div>
</template>
