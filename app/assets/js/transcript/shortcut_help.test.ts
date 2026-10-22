import { mount } from "@vue/test-utils";
import { beforeAll, describe, expect, test } from "vitest";
import ShortcutHelp from "./shortcut_help.vue";

// jsdom does not implement the modal methods of the dialog element.
beforeAll(() => {
    HTMLDialogElement.prototype.showModal = function () {
        this.open = true;
    };
    HTMLDialogElement.prototype.close = function () {
        this.open = false;
    };
});

function mountHelp() {
    return mount(ShortcutHelp, {
        global: { mocks: { $t: (key: string) => key } },
        attachTo: document.body,
    });
}

function dialog(wrapper: ReturnType<typeof mountHelp>) {
    return wrapper.find("dialog").element as HTMLDialogElement;
}

describe("ShortcutHelp", () => {
    test("the button opens the dialog", async () => {
        const wrapper = mountHelp();

        await wrapper.find(".shortcut-help__open").trigger("click");

        expect(dialog(wrapper).open).toBe(true);
    });

    test("open() opens the dialog", () => {
        const wrapper = mountHelp();

        (wrapper.vm as unknown as { open(): void }).open();

        expect(dialog(wrapper).open).toBe(true);
    });

    test("the close button closes the dialog", async () => {
        const wrapper = mountHelp();
        await wrapper.find(".shortcut-help__open").trigger("click");

        await wrapper.find(".shortcut-help__close").trigger("click");

        expect(dialog(wrapper).open).toBe(false);
    });

    // A click on the backdrop has the dialog element itself as its target.
    test("a click on the backdrop closes the dialog", async () => {
        const wrapper = mountHelp();
        await wrapper.find(".shortcut-help__open").trigger("click");

        await wrapper.find("dialog").trigger("click");

        expect(dialog(wrapper).open).toBe(false);
    });

    test("a click inside the dialog leaves it open", async () => {
        const wrapper = mountHelp();
        await wrapper.find(".shortcut-help__open").trigger("click");

        await wrapper.find(".shortcut-help__body").trigger("click");

        expect(dialog(wrapper).open).toBe(true);
    });
});
