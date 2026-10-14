<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = withDefaults(
    defineProps<{
        label: string;
        side?: "left" | "right";
        mode?: "overlay" | "docked";
    }>(),
    { side: "right", mode: "overlay" },
);

const open = defineModel<boolean>("open", { default: false });

// Below this width the content cannot move aside, so a docked drawer behaves
// as an overlay. The same width is used in transcript_drawer.css.
const wideViewport = window.matchMedia("(min-width: 64rem)");
const viewportIsWide = ref(wideViewport.matches);

function updateViewportWidth(event: MediaQueryListEvent) {
    viewportIsWide.value = event.matches;
}

onMounted(() => {
    wideViewport.addEventListener("change", updateViewportWidth);
});

const docked = computed(() => props.mode === "docked" && viewportIsWide.value);

function openDrawer() {
    open.value = true;
}

function closeDrawer() {
    open.value = false;
}

// A docked drawer stays open on Escape, because the user works in the
// transcript beside it and Escape cancels the popovers there.
function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape" && !docked.value) closeDrawer();
}

watch(open, (isOpen) => {
    if (isOpen) {
        document.addEventListener("keydown", handleKeydown);
    } else {
        document.removeEventListener("keydown", handleKeydown);
    }
});

onBeforeUnmount(() => {
    wideViewport.removeEventListener("change", updateViewportWidth);
    document.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
    <button
        v-show="!open"
        class="transcript-drawer__tab"
        :class="`transcript-drawer__tab--${side}`"
        :title="$t('open_panel')"
        @click="openDrawer"
    >
        <span class="transcript-drawer__tab-label">{{ label }}</span>
    </button>
    <div
        v-if="!docked"
        v-show="open"
        class="transcript-drawer__backdrop"
        @click="closeDrawer"
    ></div>
    <aside
        class="transcript-drawer"
        :class="[
            `transcript-drawer--${side}`,
            {
                'transcript-drawer--docked': docked,
                'transcript-drawer--open': open,
            },
        ]"
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
