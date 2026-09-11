import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import { useMessagesStore } from "./messages_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("messages store", () => {
    test("add appends a message with a unique id", () => {
        const store = useMessagesStore();

        const first = store.add("success", "Saved");
        const second = store.add("error", "Failed");

        expect(first).not.toBe(second);
        expect(store.messages).toEqual([
            { id: first, level: "success", text: "Saved" },
            { id: second, level: "error", text: "Failed" },
        ]);
    });

    test("remove drops the message with the given id", () => {
        const store = useMessagesStore();
        const first = store.add("success", "Saved");
        const second = store.add("error", "Failed");

        store.remove(first);

        expect(store.messages.map((message) => message.id)).toEqual([second]);
    });
});
