import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import Message from "./message.vue";
import type { MessageLevel } from "./messages_store";

function mountMessage(level: MessageLevel, text = "Text") {
    return mount(Message, {
        props: { level, text },
        global: { mocks: { $t: (key: string) => key } },
    });
}

describe("Message", () => {
    test("renders the level, icon and text", () => {
        const wrapper = mountMessage("success", "Saved");

        expect(wrapper.attributes("data-level")).toBe("success");
        expect(wrapper.attributes("role")).toBe("status");
        expect(wrapper.find(".message__icon svg").exists()).toBe(true);
        expect(wrapper.find(".message__text").text()).toBe("Saved");
    });

    test("an error has the alert role", () => {
        const wrapper = mountMessage("error");

        expect(wrapper.attributes("role")).toBe("alert");
    });

    test("only errors and warnings get a close button", () => {
        expect(mountMessage("success").find(".message__close").exists()).toBe(
            false,
        );
        expect(mountMessage("info").find(".message__close").exists()).toBe(
            false,
        );
        expect(mountMessage("warning").find(".message__close").exists()).toBe(
            true,
        );
        expect(mountMessage("error").find(".message__close").exists()).toBe(
            true,
        );
    });

    test("the close button emits dismiss", async () => {
        const wrapper = mountMessage("error");

        await wrapper.find(".message__close").trigger("click");

        expect(wrapper.emitted("dismiss")).toHaveLength(1);
    });

    test("the end of the dismiss animation emits dismiss", async () => {
        const wrapper = mountMessage("success");

        await wrapper.trigger("animationend", {
            animationName: "message-dismiss",
        });

        expect(wrapper.emitted("dismiss")).toHaveLength(1);
    });

    test("other animations do not emit dismiss", async () => {
        const wrapper = mountMessage("success");

        await wrapper.trigger("animationend", { animationName: "other" });

        expect(wrapper.emitted("dismiss")).toBeUndefined();
    });
});
