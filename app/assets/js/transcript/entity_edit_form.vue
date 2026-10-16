<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useTemplateRef } from "vue";

import CloseIcon from "../icons/close_icon.vue";
import { entityMeta, LINKABLE_TYPES } from "./entities";
import { entityProblems, hasProblems } from "./entity_matching";
import { useTranscriptStore } from "./transcript_store";
import type { EntityType } from "./types";

const props = defineProps<{
    entityId: string;
}>();

const emit = defineEmits<{
    close: [];
}>();

const store = useTranscriptStore();
const original = store.entities[props.entityId];

const name = ref(original.name);
const type = ref<EntityType>(original.type);
const aliases = ref([...original.aliases]);
const wikidataId = ref(original.wikidataId ?? "");

const nameInput = useTemplateRef<HTMLInputElement>("nameInput");
const aliasInputs = useTemplateRef<HTMLInputElement[]>("aliasInputs");

onMounted(() => nameInput.value?.focus());

const problems = computed(() =>
    entityProblems(
        {
            name: name.value,
            aliases: aliases.value,
            wikidataId: wikidataId.value.trim(),
        },
        store.entities,
        props.entityId,
    ),
);

const canConfirm = computed(() => !hasProblems(problems.value));

function addAlias() {
    aliases.value.push("");
    nextTick(() => aliasInputs.value?.at(-1)?.focus());
}

function removeAlias(index: number) {
    aliases.value.splice(index, 1);
}

function confirm() {
    if (!canConfirm.value) return;
    store.updateEntity(props.entityId, {
        name: name.value,
        type: type.value,
        aliases: aliases.value,
        wikidataId: wikidataId.value,
    });
    emit("close");
}
</script>

<template>
    <li class="entity-edit-form" @keydown.esc="emit('close')">
        <label class="entity-edit-form__field">
            <span class="form__label">{{ $t("entity_name") }}</span>
            <input
                ref="nameInput"
                v-model="name"
                type="text"
                class="form__input entity-edit-form__name"
                @keydown.enter.prevent="confirm"
                :aria-invalid="problems.emptyName || problems.nameTaken"
            />
        </label>
        <p v-if="problems.nameTaken" class="form__error">
            {{ $t("entity_name_taken") }}
        </p>
        <label class="entity-edit-form__field">
            <span class="form__label">{{ $t("entity_type") }}</span>
            <select v-model="type" class="entity-edit-form__type">
                <option v-for="option in LINKABLE_TYPES" :key="option" :value="option">
                    {{ $t(entityMeta(option)?.nameKey ?? option) }}
                </option>
            </select>
        </label>
        <fieldset class="entity-edit-form__aliases">
            <legend class="form__label">{{ $t("entity_aliases") }}</legend>
            <template v-for="(_alias, index) in aliases" :key="index">
                <div class="entity-edit-form__alias-row">
                    <input
                        ref="aliasInputs"
                        v-model="aliases[index]"
                        type="text"
                        class="form__input entity-edit-form__alias"
                        @keydown.enter.prevent="confirm"
                        :aria-label="$t('entity_aliases')"
                        :aria-invalid="problems.takenAliases[index]"
                    />
                    <button
                        type="button"
                        class="icon-button entity-edit-form__remove-alias"
                        :title="$t('entity_remove_alias')"
                        @click="removeAlias(index)"
                    >
                        <CloseIcon class="icon-button__icon" />
                    </button>
                </div>
                <p v-if="problems.takenAliases[index]" class="form__error">
                    {{ $t("entity_name_taken") }}
                </p>
            </template>
            <button
                type="button"
                class="entity-register__text-button entity-edit-form__add-alias"
                @click="addAlias"
            >
                + {{ $t("entity_add_alias") }}
            </button>
        </fieldset>
        <label class="entity-edit-form__field">
            <span class="form__label">{{ $t("entity_wikidata_id") }}</span>
            <input
                v-model="wikidataId"
                type="text"
                class="form__input entity-edit-form__wikidata"
                @keydown.enter.prevent="confirm"
                placeholder="Q567"
                :aria-invalid="problems.invalidWikidataId || problems.wikidataIdTaken"
            />
        </label>
        <p v-if="problems.wikidataIdTaken" class="form__error">
            {{ $t("entity_wikidata_taken") }}
        </p>
        <div class="entity-edit-form__actions">
            <button
                type="button"
                class="button button--primary button--small entity-edit-form__confirm"
                :disabled="!canConfirm"
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
