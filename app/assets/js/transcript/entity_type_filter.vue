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
    <ul class="cluster cluster--tiny u-list-plain u-mt-none u-mb-small entity-type-filter">
        <li v-for="type in ENTITY_TYPES" :key="type">
            <button
                type="button"
                class="pill entity-type-filter__toggle"
                :aria-pressed="isVisible(type)"
                :style="swatchStyle(type)"
                @click="view.setEntityTypeVisible(type, !isVisible(type))"
            >
                <span class="entity-type-filter__swatch"></span>
                {{ $t(entityName(type)) }}
            </button>
        </li>
    </ul>
</template>
