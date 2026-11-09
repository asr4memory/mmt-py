import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, expect, test } from "vitest";
import TabGroup from "./tab_group.vue";

const mountedWrappers: VueWrapper[] = [];

const tabs = [
    { id: "entities", label: "Entities" },
    { id: "speakers", label: "Speakers" },
    { id: "versions", label: "Versions" },
];

function mountTabGroup(props: Record<string, unknown> = {}) {
    const wrapper = mount(TabGroup, {
        attachTo: document.body,
        props: { tabs, ...props },
        slots: {
            entities: "<p>Entity list</p>",
            speakers: "<p>Speaker list</p>",
            versions: "<p>Version list</p>",
        },
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

function tab(wrapper: VueWrapper, label: string) {
    const found = wrapper
        .findAll('[role="tab"]')
        .find((candidate) => candidate.text() === label);
    if (!found) {
        throw new Error(`No tab labelled ${label}`);
    }
    return found;
}

function visiblePanelText(wrapper: VueWrapper) {
    return wrapper
        .findAll('[role="tabpanel"]')
        .filter((panel) => panel.isVisible())
        .map((panel) => panel.text());
}

afterEach(() => {
    while (mountedWrappers.length > 0) {
        mountedWrappers.pop()?.unmount();
    }
});

test("the first tab is active when no tab is selected", () => {
    const wrapper = mountTabGroup();

    expect(tab(wrapper, "Entities").attributes("aria-selected")).toBe("true");
    expect(tab(wrapper, "Speakers").attributes("aria-selected")).toBe("false");
    expect(visiblePanelText(wrapper)).toEqual(["Entity list"]);
});

test("the selected tab from the model is active", () => {
    const wrapper = mountTabGroup({ modelValue: "speakers" });

    expect(tab(wrapper, "Speakers").attributes("aria-selected")).toBe("true");
    expect(visiblePanelText(wrapper)).toEqual(["Speaker list"]);
});

test("clicking a tab shows its panel and updates the model", async () => {
    const wrapper = mountTabGroup();

    await tab(wrapper, "Speakers").trigger("click");

    expect(visiblePanelText(wrapper)).toEqual(["Speaker list"]);
    expect(wrapper.emitted("update:modelValue")).toEqual([["speakers"]]);
});

test("only the active tab is in the tab order", async () => {
    const wrapper = mountTabGroup();

    await tab(wrapper, "Speakers").trigger("click");

    expect(tab(wrapper, "Entities").attributes("tabindex")).toBe("-1");
    expect(tab(wrapper, "Speakers").attributes("tabindex")).toBe("0");
});

test("each tab controls the panel that is labelled by it", () => {
    const wrapper = mountTabGroup();

    for (const panel of wrapper.findAll('[role="tabpanel"]')) {
        const labelledBy = panel.attributes("aria-labelledby");
        const controllingTab = wrapper.get(`#${labelledBy}`);
        expect(controllingTab.attributes("aria-controls")).toBe(
            panel.attributes("id"),
        );
    }
});

test.each([
    ["Entities", "ArrowRight", "Speakers"],
    ["Speakers", "ArrowLeft", "Entities"],
    ["Versions", "ArrowRight", "Entities"],
    ["Entities", "ArrowLeft", "Versions"],
    ["Speakers", "Home", "Entities"],
    ["Entities", "End", "Versions"],
])("on %s, %s activates and focuses %s", async (start, key, expected) => {
    const wrapper = mountTabGroup();
    await tab(wrapper, start).trigger("click");

    await tab(wrapper, start).trigger("keydown", { key });

    expect(tab(wrapper, expected).attributes("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(tab(wrapper, expected).element);
});
