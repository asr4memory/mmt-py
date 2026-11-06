<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from "@floating-ui/vue";
import { onBeforeUnmount, onMounted, ref, useTemplateRef } from "vue";
import ChevronRightIcon from "../icons/chevron_right_icon.vue";

defineProps<{ label: string }>();

const isOpen = ref(false);
const root = useTemplateRef<HTMLDivElement>("root");
const button = useTemplateRef<HTMLButtonElement>("button");
const panel = useTemplateRef<HTMLDivElement>("panel");

const { floatingStyles } = useFloating(button, panel, {
    placement: "bottom-start",
    middleware: [offset(4), flip(), shift({ padding: 4 })],
    whileElementsMounted: autoUpdate,
});

function close() {
    isOpen.value = false;
}

function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && isOpen.value) {
        close();
        button.value?.focus();
    }
}

function handlePointerDown(event: Event) {
    if (!root.value?.contains(event.target as Node | null)) {
        close();
    }
}

onMounted(() => {
    document.addEventListener("keydown", handleKeydown);
    document.addEventListener("pointerdown", handlePointerDown);
});

onBeforeUnmount(() => {
    document.removeEventListener("keydown", handleKeydown);
    document.removeEventListener("pointerdown", handlePointerDown);
});
</script>

<template>
    <div ref="root" class="dropdown-panel">
        <button
            ref="button"
            type="button"
            class="button button--secondary button--small"
            :aria-expanded="isOpen"
            @click="isOpen = !isOpen"
        >
            {{ label }}
            <ChevronRightIcon class="dropdown-panel__chevron" aria-hidden="true" />
        </button>
        <!-- Rendered in place, so that Tab moves from the button into the panel. -->
        <div
            v-if="isOpen"
            ref="panel"
            class="popup dropdown-panel__panel"
            :style="floatingStyles"
        >
            <div class="popup__section">
                <slot :close="close" />
            </div>
        </div>
    </div>
</template>
