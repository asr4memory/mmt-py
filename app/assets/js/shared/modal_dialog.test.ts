import { mount } from "@vue/test-utils";
import { beforeAll, describe, expect, test } from "vitest";
import ModalDialog from "./modal_dialog.vue";

// jsdom does not implement the modal methods of the dialog element.
beforeAll(() => {
    HTMLDialogElement.prototype.showModal = function () {
        this.open = true;
    };
    HTMLDialogElement.prototype.close = function () {
        this.open = false;
    };
});

function mountModal() {
    return mount(ModalDialog, {
        props: { title: "Title text" },
        slots: { default: '<p id="content">Content</p>' },
        global: { mocks: { $t: (key: string) => key } },
        attachTo: document.body,
    });
}

function dialog(wrapper: ReturnType<typeof mountModal>) {
    return wrapper.find("dialog").element as HTMLDialogElement;
}

describe("ModalDialog", () => {
    test("is closed until open() is called", () => {
        const wrapper = mountModal();

        expect(dialog(wrapper).open).toBe(false);

        (wrapper.vm as unknown as { open(): void }).open();

        expect(dialog(wrapper).open).toBe(true);
    });

    test("opening focuses the close button", () => {
        const wrapper = mountModal();

        (wrapper.vm as unknown as { open(): void }).open();

        expect(document.activeElement).toBe(
            wrapper.find('button[aria-label="close"]').element,
        );
    });

    test("renders the slot content", () => {
        const wrapper = mountModal();

        expect(wrapper.find("#content").text()).toBe("Content");
    });

    test("the title labels the dialog", () => {
        const wrapper = mountModal();

        const heading = wrapper.find("h2");
        expect(heading.text()).toBe("Title text");
        expect(wrapper.find("dialog").attributes("aria-labelledby")).toBe(
            heading.attributes("id"),
        );
    });

    test("the close button closes the dialog", async () => {
        const wrapper = mountModal();
        (wrapper.vm as unknown as { open(): void }).open();

        await wrapper.find('button[aria-label="close"]').trigger("click");

        expect(dialog(wrapper).open).toBe(false);
    });

    // A click on the backdrop has the dialog element itself as its target.
    test("a click on the backdrop closes the dialog", async () => {
        const wrapper = mountModal();
        (wrapper.vm as unknown as { open(): void }).open();

        await wrapper.find("dialog").trigger("click");

        expect(dialog(wrapper).open).toBe(false);
    });

    test("a click on the content leaves the dialog open", async () => {
        const wrapper = mountModal();
        (wrapper.vm as unknown as { open(): void }).open();

        await wrapper.find("#content").trigger("click");

        expect(dialog(wrapper).open).toBe(true);
    });
});
