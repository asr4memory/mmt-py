<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";

const open = ref(false);

function openDrawer() {
    open.value = true;
}

function closeDrawer() {
    open.value = false;
}

function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") closeDrawer();
}

watch(open, (isOpen) => {
    if (isOpen) {
        document.addEventListener("keydown", handleKeydown);
    } else {
        document.removeEventListener("keydown", handleKeydown);
    }
});

onBeforeUnmount(() => {
    document.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
    <button
        v-show="!open"
        class="transcript-drawer__tab"
        :title="$t('open_panel')"
        @click="openDrawer"
    >
        <span class="transcript-drawer__tab-label">{{ $t("settings") }}</span>
    </button>
    <div
        v-show="open"
        class="transcript-drawer__backdrop"
        @click="closeDrawer"
    ></div>
    <aside
        class="transcript-drawer"
        :class="{ 'transcript-drawer--open': open }"
    >
        <button
            class="transcript-drawer__close"
            :title="$t('close_panel')"
            @click="closeDrawer"
        >
            &times;
        </button>
        <div class="transcript-drawer__body">
            <slot></slot>
        </div>
    </aside>
</template>
