<script setup lang="ts">
import { ENTITY_TYPES, entityMeta } from "./entities";
import { useViewSettingsStore } from "./view_settings_store";

const view = useViewSettingsStore();

function isVisible(type: string) {
    return view.visibleEntityTypes.includes(type);
}

function swatchStyle(type: string) {
    const meta = entityMeta(type);
    return meta === null ? {} : { "--swatch-color": `var(${meta.colorVar})` };
}

function entityName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}
</script>

<template>
    <ul class="cluster cluster--tiny u-list-plain u-mt-none u-mb-small toggle-group">
        <li v-for="type in ENTITY_TYPES" :key="type">
            <button
                type="button"
                class="pill toggle-group__toggle"
                :aria-pressed="isVisible(type)"
                :style="swatchStyle(type)"
                @click="view.setEntityTypeVisible(type, !isVisible(type))"
            >
                <span class="toggle-group__swatch"></span>
                {{ $t(entityName(type)) }}
            </button>
        </li>
    </ul>
</template>
