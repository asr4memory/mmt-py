<script setup lang="ts">
import CheckIcon from "../icons/check_icon.vue";
import CloseIcon from "../icons/close_icon.vue";
import { useTranscriptStore } from "./transcript_store";

const props = defineProps<{
    entityId: string;
}>();

const emit = defineEmits<{
    close: [];
}>();

const store = useTranscriptStore();

const name = store.entities[props.entityId].name;

function confirm() {
    store.deleteEntity(props.entityId);
    emit("close");
}
</script>

<template>
    <li class="entity-register-row cluster cluster--tiny entity-delete-confirmation">
        <span class="entity-delete-confirmation__question">
            <i>{{ name }}</i>{{ $t("entity_delete_confirm") }}
        </span>
        <button
            type="button"
            class="icon-button icon-button--danger entity-delete-confirmation__confirm"
            :title="$t('entity_delete')"
            :aria-label="$t('entity_delete')"
            @click="confirm"
        >
            <CheckIcon class="icon-button__icon" />
        </button>
        <button
            type="button"
            class="icon-button entity-delete-confirmation__cancel"
            :title="$t('cancel')"
            :aria-label="$t('cancel')"
            @click="emit('close')"
        >
            <CloseIcon class="icon-button__icon" />
        </button>
    </li>
</template>
