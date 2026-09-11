import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import MessageStack from "./message_stack.vue";
import { useMessagesStore } from "./messages_store";

function mountMessageStack() {
    return mount(MessageStack, {
        global: { mocks: { $t: (key: string) => key } },
    });
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("MessageStack", () => {
    test("renders nothing when there are no messages", () => {
        const wrapper = mountMessageStack();

        expect(wrapper.find(".message-stack").exists()).toBe(false);
    });

    test("renders each message with its level, icon and text", () => {
        const store = useMessagesStore();
        store.add("success", "Saved");
        store.add("error", "Failed");
        const wrapper = mountMessageStack();

        const messages = wrapper.findAll(".message");
        expect(messages).toHaveLength(2);
        expect(messages[0].attributes("data-level")).toBe("success");
        expect(messages[0].attributes("role")).toBe("status");
        expect(messages[0].find(".message__icon svg").exists()).toBe(true);
        expect(messages[0].find(".message__text").text()).toBe("Saved");
        expect(messages[1].attributes("data-level")).toBe("error");
        expect(messages[1].attributes("role")).toBe("alert");
    });

    test("only errors and warnings get a close button", () => {
        const store = useMessagesStore();
        store.add("success", "Saved");
        store.add("warning", "Careful");
        store.add("error", "Failed");
        const wrapper = mountMessageStack();

        const messages = wrapper.findAll(".message");
        expect(messages[0].find(".message__close").exists()).toBe(false);
        expect(messages[1].find(".message__close").exists()).toBe(true);
        expect(messages[2].find(".message__close").exists()).toBe(true);
    });

    test("the close button removes the message", async () => {
        const store = useMessagesStore();
        store.add("error", "Failed");
        const wrapper = mountMessageStack();

        await wrapper.find(".message__close").trigger("click");

        expect(store.messages).toEqual([]);
        expect(wrapper.find(".message").exists()).toBe(false);
    });

    test("the end of the dismiss animation removes the message", async () => {
        const store = useMessagesStore();
        store.add("success", "Saved");
        const wrapper = mountMessageStack();

        await wrapper
            .find(".message")
            .trigger("animationend", { animationName: "message-dismiss" });

        expect(store.messages).toEqual([]);
    });

    test("other animations do not remove the message", async () => {
        const store = useMessagesStore();
        store.add("success", "Saved");
        const wrapper = mountMessageStack();

        await wrapper
            .find(".message")
            .trigger("animationend", { animationName: "other" });

        expect(store.messages).toHaveLength(1);
    });
});
