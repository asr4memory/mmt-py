import { mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, expect, test } from "vitest";
import { ENTITY_TYPES } from "./entities";
import EntityTypeFilter from "./entity_type_filter.vue";
import { useViewSettingsStore } from "./view_settings_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

function mountFilter() {
    return mount(EntityTypeFilter, {
        global: { mocks: { $t: (key: string) => key } },
    });
}

// The toggles are in display order, so the toggle of a type is found by its
// position in ENTITY_TYPES.
function typeToggle(wrapper: VueWrapper, type: string) {
    return wrapper.findAll("button")[ENTITY_TYPES.indexOf(type)];
}

test("renders one toggle per entity type with its name", () => {
    const wrapper = mountFilter();

    expect(wrapper.findAll("button").map((toggle) => toggle.text())).toEqual([
        "entity_per",
        "entity_loc",
        "entity_org",
        "entity_date",
    ]);
});

test("presses the toggles of the visible types", () => {
    useViewSettingsStore().visibleEntityTypes = ["PER", "ORG"];
    const wrapper = mountFilter();

    const pressed = wrapper
        .findAll("button")
        .map((toggle) => toggle.attributes("aria-pressed"));
    expect(pressed).toEqual(["true", "false", "true", "false"]);
});

test("clicking a pressed toggle hides the type", async () => {
    const wrapper = mountFilter();

    await typeToggle(wrapper, "ORG").trigger("click");

    expect(useViewSettingsStore().visibleEntityTypes).toEqual(
        ENTITY_TYPES.filter((type) => type !== "ORG"),
    );
});

test("clicking an unpressed toggle shows the type", async () => {
    useViewSettingsStore().visibleEntityTypes = ["PER"];
    const wrapper = mountFilter();

    await typeToggle(wrapper, "LOC").trigger("click");

    expect(useViewSettingsStore().visibleEntityTypes).toEqual(["PER", "LOC"]);
});
