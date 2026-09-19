<script setup lang="ts">
import { ENTITY_LABELS, entityMeta } from "./entities";
import SpeakerLegend from "./speaker_legend.vue";

const props = defineProps<{
    showConfidence: boolean;
    showEntities: boolean;
    visibleEntityTypes: string[];
    showEdits: boolean;
    autoScroll: boolean;
}>();

const emit = defineEmits<{
    "update:showConfidence": [value: boolean];
    "update:showEntities": [value: boolean];
    "update:visibleEntityTypes": [value: string[]];
    "update:showEdits": [value: boolean];
    "update:autoScroll": [value: boolean];
}>();

// The colour of a type's swatch comes from the same metadata the transcript
// styling uses, so the legend cannot drift from the highlighting.
function swatchStyle(label: string) {
    const meta = entityMeta(label);
    return meta === null ? {} : { "background-color": `var(${meta.colorVar})` };
}

function entityName(label: string) {
    return entityMeta(label)?.nameKey ?? label;
}

// Rebuilding the list from ENTITY_LABELS keeps it in display order however
// often a type is switched off and on again.
function toggleEntityType(label: string, visible: boolean) {
    const types = ENTITY_LABELS.filter((other) =>
        other === label ? visible : props.visibleEntityTypes.includes(other),
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
        <label class="view-row">
            <input
                type="checkbox"
                class="view-toggle"
                :checked="autoScroll"
                @change="
                    $emit(
                        'update:autoScroll',
                        ($event.target as HTMLInputElement).checked,
                    )
                "
            />
            <span>{{ $t("auto_scroll") }}</span>
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
            <li v-for="label in ENTITY_LABELS" :key="label">
                <label class="view-row">
                    <input
                        type="checkbox"
                        class="view-toggle"
                        :checked="visibleEntityTypes.includes(label)"
                        :disabled="!showEntities"
                        @change="
                            toggleEntityType(
                                label,
                                ($event.target as HTMLInputElement).checked,
                            )
                        "
                    />
                    <span
                        class="entity-legend-list__swatch"
                        :style="swatchStyle(label)"
                    ></span>
                    <span>{{ $t(entityName(label)) }}</span>
                </label>
            </li>
        </ul>
    </section>

    <section class="u-mt-small">
        <h3>{{ $t("shortcuts") }}</h3>
        <div class="shortcuts">
            <div class="shortcut">
                <span class="shortcut__label">{{
                    $t("shortcut_play_pause")
                }}</span>
                <span
                    ><kbd class="kbd">Space</kbd> / <kbd class="kbd">P</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_back") }}</span>
                <kbd class="kbd">←</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_forward") }}</span>
                <kbd class="kbd">→</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_volume") }}</span>
                <span
                    ><kbd class="kbd">⇧ ↑</kbd> / <kbd class="kbd">⇧ ↓</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_mute") }}</span>
                <kbd class="kbd">M</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_speed") }}</span>
                <span
                    ><kbd class="kbd">&lt;</kbd> / <kbd class="kbd">&gt;</kbd></span
                >
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{
                    $t("shortcut_fullscreen")
                }}</span>
                <kbd class="kbd">F</kbd>
            </div>
            <div class="shortcut">
                <span class="shortcut__label">{{ $t("shortcut_jump") }}</span>
                <kbd class="kbd">J</kbd>
            </div>
        </div>
    </section>
</template>
