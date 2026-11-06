import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import { useViewSettingsStore } from "./view_settings_store";
import ViewMenu from "./view_menu.vue";

beforeEach(() => {
    setActivePinia(createPinia());
});

async function mountOpenMenu() {
    const wrapper = mount(ViewMenu, {
        global: { mocks: { $t: (key: string) => key } },
    });
    await wrapper.get("button").trigger("click");
    return wrapper;
}

function toggle(
    wrapper: Awaited<ReturnType<typeof mountOpenMenu>>,
    text: string,
) {
    const row = wrapper.findAll("label").find((label) => label.text() === text);
    if (row === undefined) {
        throw new Error(`no toggle labelled ${text}`);
    }
    return row.get("input");
}

describe("ViewMenu", () => {
    test("shows the current settings", async () => {
        const wrapper = await mountOpenMenu();

        const confidence = toggle(wrapper, "show_confidence");
        const edits = toggle(wrapper, "show_edits");
        expect((confidence.element as HTMLInputElement).checked).toBe(false);
        expect((edits.element as HTMLInputElement).checked).toBe(true);
    });

    test("writes a changed toggle to the view settings", async () => {
        const view = useViewSettingsStore();
        const wrapper = await mountOpenMenu();

        await toggle(wrapper, "show_confidence").setValue(true);
        await toggle(wrapper, "show_edits").setValue(false);

        expect(view.showConfidence).toBe(true);
        expect(view.showEdits).toBe(false);
    });
});
