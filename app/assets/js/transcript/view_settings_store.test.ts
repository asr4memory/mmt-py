import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import { ENTITY_TYPES } from "./entities";
import { useViewSettingsStore } from "./view_settings_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("useViewSettingsStore", () => {
    test("shows every entity type by default", () => {
        const view = useViewSettingsStore();

        expect(view.shownEntityTypes).toEqual(ENTITY_TYPES);
    });

    test("shows no entity type while the master toggle is off", () => {
        const view = useViewSettingsStore();

        view.showEntities = false;

        expect(view.shownEntityTypes).toEqual([]);
    });

    test("keeps the selection of types across the master toggle", () => {
        const view = useViewSettingsStore();
        view.setEntityTypeVisible("ORG", false);

        view.showEntities = false;
        view.showEntities = true;

        expect(view.shownEntityTypes).toEqual(
            ENTITY_TYPES.filter((type) => type !== "ORG"),
        );
    });

    test("restores a type in display order", () => {
        const view = useViewSettingsStore();
        view.visibleEntityTypes = ["ORG"];

        view.setEntityTypeVisible("PER", true);

        expect(view.visibleEntityTypes).toEqual(["PER", "ORG"]);
    });
});
