<script setup lang="ts">
import { ENTITY_TYPES, entityMeta } from "./entities";
import SpeakerLegend from "./speaker_legend.vue";
import { useViewSettingsStore } from "./view_settings_store";

const view = useViewSettingsStore();

// The colour of a type's swatch comes from the same metadata the transcript
// styling uses, so the legend cannot drift from the highlighting.
function swatchStyle(type: string) {
    const meta = entityMeta(type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
}

function entityName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}
</script>

<template>
    <section>
        <h3 class="u-mt-none">{{ $t("speakers") }}</h3>
        <SpeakerLegend />
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("named_entities") }}</h3>
        <label class="view-row">
            <input
                v-model="view.showEntities"
                type="checkbox"
                class="view-toggle"
            />
            <span>{{ $t("show_entities") }}</span>
        </label>
        <ul class="entity-legend-list u-mt-none u-mb-none">
            <li v-for="type in ENTITY_TYPES" :key="type">
                <label class="view-row">
                    <input
                        type="checkbox"
                        class="view-toggle"
                        :checked="view.visibleEntityTypes.includes(type)"
                        :disabled="!view.showEntities"
                        @change="
                            view.setEntityTypeVisible(
                                type,
                                ($event.target as HTMLInputElement).checked,
                            )
                        "
                    />
                    <span
                        class="entity-legend-list__swatch"
                        :style="swatchStyle(type)"
                    ></span>
                    <span>{{ $t(entityName(type)) }}</span>
                </label>
            </li>
        </ul>
    </section>
</template>
