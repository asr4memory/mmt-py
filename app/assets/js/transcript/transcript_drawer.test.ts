import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, test, vi } from "vitest";
import TranscriptDrawer from "./transcript_drawer.vue";

afterEach(() => {
    vi.unstubAllGlobals();
});

function mountDrawer(props: Record<string, unknown> = {}) {
    return mount(TranscriptDrawer, {
        props: { label: "Settings", ...props },
        slots: { default: '<p class="slotted">Panel content</p>' },
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
        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--open",
        );
    });

    test("renders slot content", () => {
        const wrapper = mountDrawer();

        expect(wrapper.find(".slotted").text()).toBe("Panel content");
    });

    test("clicking the tab opens the drawer and hides the tab", async () => {
        const wrapper = mountDrawer();

        await wrapper.find(".transcript-drawer__tab").trigger("click");

        expect(wrapper.find(".transcript-drawer").classes()).toContain(
            "transcript-drawer--open",
        );
        expect(wrapper.find(".transcript-drawer__tab").isVisible()).toBe(false);
    });

    test("the close button closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        await wrapper.find(".transcript-drawer__close").trigger("click");

        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--open",
        );
    });

    test("clicking the backdrop closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        await wrapper.find(".transcript-drawer__backdrop").trigger("click");

        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--open",
        );
    });

    test("Escape closes the drawer", async () => {
        const wrapper = mountDrawer();
        await wrapper.find(".transcript-drawer__tab").trigger("click");

        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--open",
        );
    });
});

// Replaces the matchMedia stub of the test setup with one that reports the
// given viewport width as matching or not matching the docked layout.
function stubViewport(wide: boolean) {
    vi.stubGlobal("matchMedia", (query: string) => ({
        matches: wide,
        media: query,
        addEventListener: () => {},
        removeEventListener: () => {},
    }));
}

async function openDrawer(wrapper: ReturnType<typeof mountDrawer>) {
    await wrapper.find(".transcript-drawer__tab").trigger("click");
}

function pressEscape() {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
}

describe("TranscriptDrawer label and side", () => {
    test("the tab shows the label prop", () => {
        const wrapper = mountDrawer({ label: "Entities" });

        expect(wrapper.find(".transcript-drawer__tab").text()).toBe("Entities");
    });

    test("a drawer is on the right by default", () => {
        const wrapper = mountDrawer();

        expect(wrapper.find(".transcript-drawer").classes()).toContain(
            "transcript-drawer--right",
        );
    });

    test("side left puts the drawer and its tab on the left", () => {
        const wrapper = mountDrawer({ side: "left" });

        expect(wrapper.find(".transcript-drawer").classes()).toContain(
            "transcript-drawer--left",
        );
        expect(wrapper.find(".transcript-drawer__tab").classes()).toContain(
            "transcript-drawer__tab--left",
        );
    });
});

describe("TranscriptDrawer docked mode", () => {
    test("a docked drawer carries the docked modifier class", () => {
        stubViewport(true);
        const wrapper = mountDrawer({ mode: "docked" });

        expect(wrapper.find(".transcript-drawer").classes()).toContain(
            "transcript-drawer--docked",
        );
    });

    test("an open docked drawer draws no backdrop", async () => {
        stubViewport(true);
        const wrapper = mountDrawer({ mode: "docked" });

        await openDrawer(wrapper);

        expect(wrapper.find(".transcript-drawer__backdrop").exists()).toBe(
            false,
        );
    });

    test("Escape leaves a docked drawer open", async () => {
        stubViewport(true);
        const wrapper = mountDrawer({ mode: "docked" });
        await openDrawer(wrapper);

        pressEscape();
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".transcript-drawer").classes()).toContain(
            "transcript-drawer--open",
        );
    });

    test("on a narrow viewport a docked drawer behaves as an overlay", async () => {
        stubViewport(false);
        const wrapper = mountDrawer({ mode: "docked" });
        await openDrawer(wrapper);

        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--docked",
        );
        expect(wrapper.find(".transcript-drawer__backdrop").isVisible()).toBe(
            true,
        );

        pressEscape();
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".transcript-drawer").classes()).not.toContain(
            "transcript-drawer--open",
        );
    });

    test("opening and closing emits the open state", async () => {
        stubViewport(true);
        const wrapper = mountDrawer({ mode: "docked" });
        await openDrawer(wrapper);

        await wrapper.find(".transcript-drawer__close").trigger("click");

        expect(wrapper.emitted("update:open")).toEqual([[true], [false]]);
    });
});
