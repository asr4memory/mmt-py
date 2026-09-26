import { type VueWrapper, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import { ENTITY_TYPES } from "./entities";
import TranscriptSidebar from "./transcript_sidebar.vue";

beforeEach(() => {
    setActivePinia(createPinia());
});

function mountSidebar(props: Record<string, unknown> = {}) {
    return mount(TranscriptSidebar, {
        props: {
            showConfidence: false,
            showEntities: true,
            showEdits: true,
            autoScroll: false,
            visibleEntityTypes: [...ENTITY_TYPES],
            ...props,
        },
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
    test("puts the master toggle in the entity section, not in the view section", () => {
        const wrapper = mountSidebar();

        expect(section(wrapper, "named_entities").text()).toContain(
            "show_entities",
        );
        expect(section(wrapper, "view").text()).not.toContain("show_entities");
    });

    test("renders one toggle per entity type", () => {
        const wrapper = mountSidebar();

        expect(typeToggles(wrapper)).toHaveLength(ENTITY_TYPES.length);
    });

    test("checks the visible types", () => {
        const visible = ENTITY_TYPES.filter((type) => type !== "LOC");
        const wrapper = mountSidebar({ visibleEntityTypes: visible });

        const checked = typeToggles(wrapper).map(
            (toggle) => (toggle.element as HTMLInputElement).checked,
        );
        expect(checked).toEqual(ENTITY_TYPES.map((type) => type !== "LOC"));
    });

    test("drops the type from the visible types when it is unchecked", async () => {
        const wrapper = mountSidebar({
            visibleEntityTypes: [...ENTITY_TYPES],
        });

        await typeToggles(wrapper)[ENTITY_TYPES.indexOf("ORG")].setValue(false);

        expect(wrapper.emitted("update:visibleEntityTypes")).toEqual([
            [ENTITY_TYPES.filter((type) => type !== "ORG")],
        ]);
    });

    test("adds the type to the visible types in display order when it is checked", async () => {
        const wrapper = mountSidebar({ visibleEntityTypes: ["ORG"] });

        await typeToggles(wrapper)[ENTITY_TYPES.indexOf("PER")].setValue(true);

        expect(wrapper.emitted("update:visibleEntityTypes")).toEqual([
            [["PER", "ORG"]],
        ]);
    });

    test("disables the type toggles while the master toggle is off", () => {
        const wrapper = mountSidebar({ showEntities: false });

        for (const toggle of typeToggles(wrapper)) {
            expect((toggle.element as HTMLInputElement).disabled).toBe(true);
        }
    });
});
