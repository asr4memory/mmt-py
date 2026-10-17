<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { entityMeta, nameTaken } from "./entities";
import { useTranscriptStore } from "./transcript_store";

const WIKIDATA_ID = /^Q[1-9][0-9]*$/;

const props = defineProps<{
    entityId: string;
}>();

const emit = defineEmits<{
    close: [];
}>();

const store = useTranscriptStore();
const { entities } = storeToRefs(store);

// Editing (UC-6). The type is shown but cannot be changed.
const entity = entities.value[props.entityId];
const name = ref(entity.name);
const wikidataId = ref(entity.wikidataId ?? "");

const typeName = computed(
    () => entityMeta(entity.type)?.nameKey ?? entity.type,
);

const nameIsTaken = computed(() =>
    nameTaken(entities.value, name.value.trim(), props.entityId),
);
const trimmedWikidataId = computed(() => wikidataId.value.trim());
// An empty field is valid and means no identifier.
const wikidataMalformed = computed(
    () =>
        trimmedWikidataId.value !== "" &&
        !WIKIDATA_ID.test(trimmedWikidataId.value),
);
// Whether another entity has the Wikidata ID (invariant 5).
const wikidataIsTaken = computed(
    () =>
        trimmedWikidataId.value !== "" &&
        Object.entries(entities.value).some(
            ([id, other]) =>
                id !== props.entityId &&
                other.wikidataId === trimmedWikidataId.value,
        ),
);
const canSave = computed(
    () =>
        name.value.trim() !== "" &&
        !nameIsTaken.value &&
        !wikidataMalformed.value &&
        !wikidataIsTaken.value,
);

function confirm() {
    if (!canSave.value) return;
    store.updateEntity(
        props.entityId,
        name.value.trim(),
        trimmedWikidataId.value === "" ? null : trimmedWikidataId.value,
    );
    emit("close");
}
</script>

<template>
    <li class="entity-register-row stack stack--tiny entity-form entity-edit-form">
        <input
            v-model="name"
            type="text"
            class="entity-edit-form__name"
            :aria-label="$t('entity_name')"
            @keyup.enter="confirm"
            @keyup.esc="emit('close')"
        />
        <p v-if="nameIsTaken" class="entity-form__error">
            {{ $t("entity_name_taken") }}
        </p>
        <p class="u-color-muted u-font-small">
            {{ $t("entity_type") }}: {{ $t(typeName) }}
        </p>
        <input
            v-model="wikidataId"
            type="text"
            class="entity-edit-form__wikidata"
            :aria-label="$t('entity_wikidata_id')"
            :aria-invalid="wikidataMalformed ? 'true' : 'false'"
            :placeholder="$t('entity_wikidata_id')"
            @keyup.enter="confirm"
            @keyup.esc="emit('close')"
        />
        <p v-if="wikidataIsTaken" class="entity-form__error">
            {{ $t("entity_wikidata_taken") }}
        </p>
        <div class="cluster cluster--tiny">
            <button
                type="button"
                class="button button--primary button--small entity-edit-form__confirm"
                :disabled="!canSave"
                @click="confirm"
            >
                {{ $t("save") }}
            </button>
            <button
                type="button"
                class="button button--secondary button--small entity-edit-form__cancel"
                @click="emit('close')"
            >
                {{ $t("cancel") }}
            </button>
        </div>
    </li>
</template>
