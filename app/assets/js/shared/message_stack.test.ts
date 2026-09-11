import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import Message from "./message.vue";
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

    test("renders one Message per store entry", () => {
        const store = useMessagesStore();
        store.add("success", "Saved");
        store.add("error", "Failed");
        const wrapper = mountMessageStack();

        const messages = wrapper.findAllComponents(Message);
        expect(messages).toHaveLength(2);
        expect(messages[0].props()).toEqual({ level: "success", text: "Saved" });
        expect(messages[1].props()).toEqual({ level: "error", text: "Failed" });
    });

    test("removes a message from the store when it is dismissed", async () => {
        const store = useMessagesStore();
        const first = store.add("error", "Failed");
        const second = store.add("error", "Also failed");
        const wrapper = mountMessageStack();

        await wrapper.findAllComponents(Message)[0].vm.$emit("dismiss");

        expect(store.messages.map((message) => message.id)).toEqual([second]);
        expect(store.messages.map((message) => message.id)).not.toContain(first);
    });
});
