<script setup lang="ts">
import { useId, useTemplateRef } from "vue";
import CloseIcon from "../icons/close_icon.vue";

defineProps<{ title: string }>();

const titleId = useId();
const dialog = useTemplateRef<HTMLDialogElement>("dialog");
const closeButton = useTemplateRef<HTMLButtonElement>("closeButton");

function open() {
    dialog.value?.showModal();
    closeButton.value?.focus();
}

function close() {
    dialog.value?.close();
}

// The backdrop belongs to the dialog element, so a click on it has the
// dialog itself as its target. The content is wrapped in an element that
// fills the dialog, so a click inside never has that target.
function closeOnBackdropClick(event: MouseEvent) {
    if (event.target === dialog.value) {
        close();
    }
}

defineExpose({ open, close });
</script>

<template>
    <dialog
        ref="dialog"
        class="modal-dialog"
        :aria-labelledby="titleId"
        @click="closeOnBackdropClick"
    >
        <div class="modal-dialog__body">
            <div class="modal-dialog__header">
                <h2 :id="titleId" class="modal-dialog__title">{{ title }}</h2>
                <button
                    ref="closeButton"
                    type="button"
                    class="icon-button modal-dialog__close"
                    :title="$t('close')"
                    :aria-label="$t('close')"
                    @click="close"
                >
                    <CloseIcon class="icon-button__icon" />
                </button>
            </div>
            <slot />
        </div>
    </dialog>
</template>
