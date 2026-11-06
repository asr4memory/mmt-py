import { type VueWrapper, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import { ENTITY_TYPES } from "./entities";
import TranscriptSidebar from "./transcript_sidebar.vue";
import { useViewSettingsStore } from "./view_settings_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

function mountSidebar() {
    return mount(TranscriptSidebar, {
        global: {
            mocks: { $t: (key: string) => key },
            stubs: { SpeakerLegend: true },
        },
    });
}

// The sidebar groups its controls into sections headed by an h3 whose text is
// the i18n key, because $t is mocked with the identity function.
function section(wrapper: VueWrapper, heading: string) {
    const found = wrapper
        .findAll("section")
        .find((candidate) => candidate.find("h3").text() === heading);
    if (found === undefined) {
        throw new Error(`no section headed ${heading}`);
    }
    return found;
}

function typeToggles(wrapper: VueWrapper) {
    return section(wrapper, "named_entities").findAll(
        ".entity-legend-list input[type='checkbox']",
    );
}

describe("TranscriptSidebar entity section", () => {
    test("renders one toggle per entity type", () => {
        const wrapper = mountSidebar();

        expect(typeToggles(wrapper)).toHaveLength(ENTITY_TYPES.length);
    });

    test("checks the visible types", () => {
        const visible = ENTITY_TYPES.filter((type) => type !== "LOC");
        useViewSettingsStore().visibleEntityTypes = visible;
        const wrapper = mountSidebar();

        const checked = typeToggles(wrapper).map(
            (toggle) => (toggle.element as HTMLInputElement).checked,
        );
        expect(checked).toEqual(ENTITY_TYPES.map((type) => type !== "LOC"));
    });

    test("drops the type from the visible types when it is unchecked", async () => {
        const wrapper = mountSidebar();

        await typeToggles(wrapper)[ENTITY_TYPES.indexOf("ORG")].setValue(false);

        expect(useViewSettingsStore().visibleEntityTypes).toEqual(
            ENTITY_TYPES.filter((type) => type !== "ORG"),
        );
    });

    test("disables the type toggles while the master toggle is off", () => {
        useViewSettingsStore().showEntities = false;
        const wrapper = mountSidebar();

        for (const toggle of typeToggles(wrapper)) {
            expect((toggle.element as HTMLInputElement).disabled).toBe(true);
        }
    });
});
