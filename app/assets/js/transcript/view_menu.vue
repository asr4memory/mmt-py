<script setup lang="ts">
import DropdownPanel from "../shared/dropdown_panel.vue";
import { useViewSettingsStore } from "./view_settings_store";

const view = useViewSettingsStore();
</script>

<template>
    <DropdownPanel :label="$t('view')">
        <label class="checkbox cluster u-font-small">
            <input
                v-model="view.showConfidence"
                type="checkbox"
                class="checkbox__input"
            />
            <span>{{ $t("show_confidence") }}</span>
        </label>
        <label class="checkbox cluster u-font-small">
            <input
                v-model="view.showEdits"
                type="checkbox"
                class="checkbox__input"
            />
            <span>{{ $t("show_edits") }}</span>
        </label>
        <label class="checkbox cluster u-font-small">
            <input
                v-model="view.showEntities"
                type="checkbox"
                class="checkbox__input"
            />
            <span>{{ $t("show_entities") }}</span>
        </label>
    </DropdownPanel>
</template>
