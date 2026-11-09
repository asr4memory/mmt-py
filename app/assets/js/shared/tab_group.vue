<script setup lang="ts">
import { computed, nextTick, useId } from "vue";

export interface Tab {
    id: string;
    label: string;
}

const props = defineProps<{ tabs: Tab[] }>();

// Without a model value the first tab is active.
const selected = defineModel<string>();

const active = computed(() => selected.value ?? props.tabs[0]?.id);

const idPrefix = useId();

function tabId(id: string) {
    return `${idPrefix}-tab-${id}`;
}

function panelId(id: string) {
    return `${idPrefix}-panel-${id}`;
}

async function activate(index: number) {
    const id = props.tabs[index].id;
    selected.value = id;
    await nextTick();
    document.getElementById(tabId(id))?.focus();
}

// Arrow keys move to the neighbouring tab and wrap at both ends.
function handleKeydown(event: KeyboardEvent, index: number) {
    const count = props.tabs.length;
    const targets: Record<string, number> = {
        ArrowLeft: (index - 1 + count) % count,
        ArrowRight: (index + 1) % count,
        Home: 0,
        End: count - 1,
    };
    const target = targets[event.key];
    if (target === undefined) {
        return;
    }
    event.preventDefault();
    activate(target);
}
</script>

<template>
    <div class="tab-group">
        <div role="tablist" class="tab-group__list">
            <button
                v-for="(tab, index) in tabs"
                :id="tabId(tab.id)"
                :key="tab.id"
                type="button"
                role="tab"
                class="tab-group__tab"
                :aria-selected="tab.id === active"
                :aria-controls="panelId(tab.id)"
                :tabindex="tab.id === active ? 0 : -1"
                @click="selected = tab.id"
                @keydown="handleKeydown($event, index)"
            >
                {{ tab.label }}
            </button>
        </div>
        <!-- Inactive panels stay mounted, so that their state is kept. -->
        <div
            v-for="tab in tabs"
            v-show="tab.id === active"
            :id="panelId(tab.id)"
            :key="tab.id"
            role="tabpanel"
            class="tab-group__panel"
            :aria-labelledby="tabId(tab.id)"
            tabindex="0"
        >
            <slot :name="tab.id"></slot>
        </div>
    </div>
</template>
