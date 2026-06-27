<script setup lang="ts">
import SpeakerLegend from "./speaker_legend.vue";

defineProps<{
    showConfidence: boolean;
    showEntities: boolean;
    showEdits: boolean;
    autoScroll: boolean;
}>();

defineEmits<{
    "update:showConfidence": [value: boolean];
    "update:showEntities": [value: boolean];
    "update:showEdits": [value: boolean];
    "update:autoScroll": [value: boolean];
}>();
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
        <ul class="entity-legend-list u-mt-none u-mb-none">
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--per"
                ></span>
                {{ $t("entity_per") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--loc"
                ></span>
                {{ $t("entity_loc") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--org"
                ></span>
                {{ $t("entity_org") }}
            </li>
            <li class="entity-legend-list__item">
                <span
                    class="entity-legend-list__swatch entity-legend-list__swatch--date"
                ></span>
                {{ $t("entity_date") }}
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
        </div>
    </section>
</template>
