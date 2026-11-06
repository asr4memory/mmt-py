import { type VueWrapper, mount } from "@vue/test-utils";
import { afterEach, describe, expect, test } from "vitest";
import { h } from "vue";
import DropdownPanel from "./dropdown_panel.vue";

const mountedWrappers: VueWrapper[] = [];

function mountDropdown(
    slot: (props: { close: () => void }) => unknown = () =>
        h("input", { class: "content", type: "checkbox" }),
) {
    const wrapper = mount(DropdownPanel, {
        attachTo: document.body,
        props: { label: "View" },
        slots: { default: slot as () => never },
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

function toggle(wrapper: VueWrapper) {
    return wrapper.get("button[aria-expanded]");
}

async function mountOpenDropdown() {
    const wrapper = mountDropdown();
    await toggle(wrapper).trigger("click");
    return wrapper;
}

function pressKey(key: string) {
    document.dispatchEvent(new KeyboardEvent("keydown", { key }));
}

function pressPointerOn(target: Element) {
    target.dispatchEvent(new Event("pointerdown", { bubbles: true }));
}

afterEach(() => {
    while (mountedWrappers.length > 0) {
        mountedWrappers.pop()?.unmount();
    }
});

describe("DropdownPanel", () => {
    test("hides the content until the button is clicked", async () => {
        const wrapper = mountDropdown();

        expect(toggle(wrapper).text()).toBe("View");
        expect(toggle(wrapper).attributes("aria-expanded")).toBe("false");
        expect(wrapper.find(".content").exists()).toBe(false);

        await toggle(wrapper).trigger("click");

        expect(toggle(wrapper).attributes("aria-expanded")).toBe("true");
        expect(wrapper.find(".content").exists()).toBe(true);
    });

    test("closes on a second click on the button", async () => {
        const wrapper = await mountOpenDropdown();

        pressPointerOn(toggle(wrapper).element);
        await toggle(wrapper).trigger("click");

        expect(wrapper.find(".content").exists()).toBe(false);
    });

    test("stays open when the content is used", async () => {
        const wrapper = await mountOpenDropdown();

        pressPointerOn(wrapper.get(".content").element);
        await wrapper.get(".content").setValue(true);

        expect(wrapper.find(".content").exists()).toBe(true);
    });

    test("closes on a pointer press outside", async () => {
        const wrapper = await mountOpenDropdown();

        pressPointerOn(document.body);
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".content").exists()).toBe(false);
    });

    test("closes on Escape and returns the focus to the button", async () => {
        const wrapper = await mountOpenDropdown();
        (wrapper.get(".content").element as HTMLElement).focus();

        pressKey("Escape");
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".content").exists()).toBe(false);
        expect(document.activeElement).toBe(toggle(wrapper).element);
    });

    test("leaves the focus alone on Escape while closed", () => {
        const wrapper = mountDropdown();

        pressKey("Escape");

        expect(document.activeElement).not.toBe(toggle(wrapper).element);
    });

    test("lets the content close the panel", async () => {
        const wrapper = mountDropdown(({ close }) =>
            h("button", { class: "action", onClick: close }, "Action"),
        );
        await toggle(wrapper).trigger("click");

        await wrapper.get(".action").trigger("click");

        expect(wrapper.find(".action").exists()).toBe(false);
    });

    test("removes its listeners when it is unmounted", async () => {
        const wrapper = await mountOpenDropdown();
        const button = toggle(wrapper).element as HTMLElement;
        const focus = () => {
            throw new Error("the unmounted dropdown handled Escape");
        };
        button.focus = focus;

        wrapper.unmount();
        mountedWrappers.pop();

        expect(() => pressKey("Escape")).not.toThrow();
    });
});
