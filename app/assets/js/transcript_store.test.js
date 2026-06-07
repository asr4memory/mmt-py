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

test("renameSpeaker updates the legend entry and keeps its color", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    const color = store.speakers[0].color;
    store.renameSpeaker("Alice", "Bob");
    expect(store.speakers).toHaveLength(1);
    expect(store.speakers[0].name).toBe("Bob");
    expect(store.speakers[0].color).toBe(color);
});

test("renameSpeaker updates segments and words and marks them dirty", () => {
    const store = useTranscriptStore();
    store.speakers = [{ name: "Alice", color: "#000" }];
    store.segments = [
        {
            id: "1",
            speaker: "Alice",
            words: [
                { id: "w1", word: "hi", speaker: "Alice" },
                { id: "w2", word: "there", speaker: "Bob" },
            ],
        },
        {
            id: "2",
            speaker: "Bob",
            words: [{ id: "w3", word: "yo", speaker: "Bob" }],
        },
    ];
    store.renameSpeaker("Alice", "Carol");
    expect(store.segments[0].speaker).toBe("Carol");
    expect(store.segments[0].words[0].speaker).toBe("Carol");
    expect(store.segments[0].words[1].speaker).toBe("Bob");
    expect(store.segments[0].dirty).toBe(true);
    expect(store.segments[1].speaker).toBe("Bob");
    expect(store.segments[1].dirty).toBeUndefined();
});

test("renameSpeaker throws when the new name already exists", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    store.addSpeaker("Bob");
    expect(() => store.renameSpeaker("Alice", "Bob")).toThrow(
        "Speaker already exists: Bob",
    );
});

test("renameSpeaker throws when the speaker does not exist", () => {
    const store = useTranscriptStore();
    expect(() => store.renameSpeaker("Ghost", "Bob")).toThrow(
        "Speaker does not exist: Ghost",
    );
});

test("renameSpeaker is a no-op when the name is unchanged", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    store.segments = [{ id: "1", speaker: "Alice", words: [] }];
    store.renameSpeaker("Alice", "Alice");
    expect(store.speakers[0].name).toBe("Alice");
    expect(store.segments[0].dirty).toBeUndefined();
});
