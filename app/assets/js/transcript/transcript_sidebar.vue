<script setup lang="ts">
import { ENTITY_TYPES, entityMeta } from "./entities";
import SpeakerLegend from "./speaker_legend.vue";

const props = defineProps<{
    showConfidence: boolean;
    showEntities: boolean;
    visibleEntityTypes: string[];
    showEdits: boolean;
}>();

const emit = defineEmits<{
    "update:showConfidence": [value: boolean];
    "update:showEntities": [value: boolean];
    "update:visibleEntityTypes": [value: string[]];
    "update:showEdits": [value: boolean];
}>();

// The colour of a type's swatch comes from the same metadata the transcript
// styling uses, so the legend cannot drift from the highlighting.
function swatchStyle(type: string) {
    const meta = entityMeta(type);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
}

function entityName(type: string) {
    return entityMeta(type)?.nameKey ?? type;
}

// Rebuilding the list from ENTITY_TYPES keeps it in display order however
// often a type is switched off and on again.
function toggleEntityType(type: string, visible: boolean) {
    const types = ENTITY_TYPES.filter((other) =>
        other === type ? visible : props.visibleEntityTypes.includes(other),
    );
    emit("update:visibleEntityTypes", types);
}
</script>

<template>
    <section>
        <h3 class="u-mt-none">{{ $t("view") }}</h3>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showConfidence"
                @change="
                    $emit(
                        'update:showConfidence',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_confidence") }}</span>
        </label>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showEdits"
                @change="
                    $emit(
                        'update:showEdits',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_edits") }}</span>
        </label>
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("speakers") }}</h3>
        <SpeakerLegend />
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("named_entities") }}</h3>
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="showEntities"
                @change="
                    $emit(
                        'update:showEntities',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("show_entities") }}</span>
        </label>
        <ul class="entity-legend-list u-mt-none u-mb-none">
            <li v-for="type in ENTITY_TYPES" :key="type">
                <label class="view-row">
                    <input
                        type="checkbox"
                        class="view-toggle"
                        :checked="visibleEntityTypes.includes(type)"
                        :disabled="!showEntities"
                        @change="
                            toggleEntityType(
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
