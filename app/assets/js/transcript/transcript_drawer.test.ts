import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import TranscriptDrawer from "./transcript_drawer.vue";

function mountDrawer() {
    return mount(TranscriptDrawer, {
        slots: { default: "<p class=\"slotted\">Panel content</p>" },
        global: {
            mocks: { $t: (key: string) => key },
        },
        attachTo: document.body,
    });
}

describe("TranscriptDrawer", () => {
    test("starts closed: tab visible, panel not open", () => {
        const wrapper = mountDrawer();

        expect(wrapper.find(".transcript-drawer__tab").isVisible()).toBe(true);
        expect(
            wrapper.find(".transcript-drawer").classes(),
        ).not.toContain("transcript-drawer--open");
    });

    test("renders slot content", () => {
        const wrapper = mountDrawer();

        expect(wrapper.find(".slotted").text()).toBe("Panel content");
    });

    test("clicking the tab opens the drawer and hides the tab", async () => {
        const wrapper = mountDrawer();

        await wrapper.find(".transcript-drawer__tab").trigger("click");

        expect(
            wrapper.find(".transcript-drawer").classes(),
        ).toContain("transcript-drawer--open");
        expect(wrapper.find(".transcript-drawer__tab").isVisible()).toBe(false);
    });

    test("the close button closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        await wrapper.find(".transcript-drawer__close").trigger("click");

        expect(
            wrapper.find(".transcript-drawer").classes(),
        ).not.toContain("transcript-drawer--open");
    });

    test("clicking the backdrop closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        await wrapper.find(".transcript-drawer__backdrop").trigger("click");

        expect(
            wrapper.find(".transcript-drawer").classes(),
        ).not.toContain("transcript-drawer--open");
    });

    test("Escape closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        document.dispatchEvent(
            new KeyboardEvent("keydown", { key: "Escape" }),
        );
        await wrapper.vm.$nextTick();

        expect(
            wrapper.find(".transcript-drawer").classes(),
        ).not.toContain("transcript-drawer--open");
    });
});
