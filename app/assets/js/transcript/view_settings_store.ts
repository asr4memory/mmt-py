import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { ENTITY_TYPES } from "./entities";

// How the transcript is displayed. Nothing here is part of the content, so a
// change does not mark the transcript unsaved.
export const useViewSettingsStore = defineStore("viewSettings", () => {
    const showConfidence = ref(false);
    const showEdits = ref(true);
    const showEntities = ref(true);
    const visibleEntityTypes = ref<string[]>([...ENTITY_TYPES]);

    // The master toggle sits in front of the per-type selection.
    const shownEntityTypes = computed(() =>
        showEntities.value ? visibleEntityTypes.value : [],
    );

    // Rebuilding the list from ENTITY_TYPES keeps it in display order however
    // often a type is switched off and on again.
    function setEntityTypeVisible(type: string, visible: boolean) {
        visibleEntityTypes.value = ENTITY_TYPES.filter((other) =>
            other === type ? visible : visibleEntityTypes.value.includes(other),
        );
    }

    return {
        showConfidence,
        showEdits,
        showEntities,
        visibleEntityTypes,
        shownEntityTypes,
        setEntityTypeVisible,
    };
});
