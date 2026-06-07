import { expect, test, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useTranscriptStore } from "./transcript_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

test("addSpeaker adds a new speaker with a color", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    expect(store.speakers).toHaveLength(1);
    expect(store.speakers[0].name).toBe("Alice");
    expect(store.speakers[0].color).toBeDefined();
});

test("addSpeaker ignores empty names", () => {
    const store = useTranscriptStore();
    store.addSpeaker("  ");
    expect(store.speakers).toHaveLength(0);
});

test("addSpeaker throws on duplicate names", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    expect(() => store.addSpeaker("Alice")).toThrow("Speaker already exists: Alice");
});
