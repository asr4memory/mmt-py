<script setup lang="ts">
import DropdownPanel from "../shared/dropdown_panel.vue";
import { useViewSettingsStore } from "./view_settings_store";

const view = useViewSettingsStore();
</script>

<template>
    <DropdownPanel :label="$t('view')">
        <label class="view-row">
            <input
                v-model="view.showConfidence"
                type="checkbox"
                class="view-toggle"
            />
            <span>{{ $t("show_confidence") }}</span>
        </label>
        <label class="view-row">
            <input
                v-model="view.showEdits"
                type="checkbox"
                class="view-toggle"
            />
            <span>{{ $t("show_edits") }}</span>
        </label>
    </DropdownPanel>
</template>
