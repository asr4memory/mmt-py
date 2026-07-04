import { expect, test, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useTranscriptStore } from "./transcript_store";

beforeEach(() => {
    setActivePinia(createPinia());
});

test("addSpeaker adds a new speaker with an id and a color", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    expect(store.speakers).toHaveLength(1);
    expect(store.speakers[0].name).toBe("Alice");
    expect(store.speakers[0].id).toBeTruthy();
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
    expect(() => store.addSpeaker("Alice")).toThrow(
        "Speaker already exists: Alice",
    );
});

test("renameSpeaker updates the legend entry and keeps its id and color", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    const { id, color } = store.speakers[0];
    store.renameSpeaker(id, "Bob");
    expect(store.speakers).toHaveLength(1);
    expect(store.speakers[0].id).toBe(id);
    expect(store.speakers[0].name).toBe("Bob");
    expect(store.speakers[0].color).toBe(color);
});

test("renameSpeaker leaves speakerId references intact and marks referencing segments dirty", () => {
    const store = useTranscriptStore();
    store.speakers = [
        { id: "spk_a", name: "Alice", color: "#000000" },
        { id: "spk_b", name: "Bob", color: "#111111" },
    ];
    store.segments = [
        {
            id: "1",
            speakerId: "spk_a",
            words: [
                { id: "w1", word: "hi", speakerId: "spk_a" },
                { id: "w2", word: "there", speakerId: "spk_b" },
            ],
        },
        {
            id: "2",
            speakerId: "spk_b",
            words: [{ id: "w3", word: "yo", speakerId: "spk_b" }],
        },
        {
            id: "3",
            speakerId: "spk_b",
            words: [{ id: "w4", word: "again", speakerId: "spk_a" }],
        },
    ] as any;
    store.renameSpeaker("spk_a", "Carol");

    // References are by id, so they do not change.
    expect(store.segments[0].speakerId).toBe("spk_a");
    expect(store.segments[0].words[0].speakerId).toBe("spk_a");

    // Segment 1 references spk_a directly; segment 3 via one of its words.
    expect(store.segments[0].dirty).toBe(true);
    expect(store.segments[1].dirty).toBeUndefined();
    expect(store.segments[2].dirty).toBe(true);
});

test("renameSpeaker throws when the new name already exists", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    store.addSpeaker("Bob");
    const aliceId = store.speakers[0].id;
    expect(() => store.renameSpeaker(aliceId, "Bob")).toThrow(
        "Speaker already exists: Bob",
    );
});

test("renameSpeaker throws when the speaker does not exist", () => {
    const store = useTranscriptStore();
    expect(() => store.renameSpeaker("spk_ghost", "Bob")).toThrow(
        "Speaker does not exist: spk_ghost",
    );
});

test("renameSpeaker is a no-op when the name is unchanged", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    const aliceId = store.speakers[0].id;
    store.segments = [{ id: "1", speakerId: aliceId, words: [] }] as any;
    store.renameSpeaker(aliceId, "Alice");
    expect(store.speakers[0].name).toBe("Alice");
    expect(store.segments[0].dirty).toBeUndefined();
});

test("deleteSpeaker removes the speaker from the legend", () => {
    const store = useTranscriptStore();
    store.addSpeaker("Alice");
    store.addSpeaker("Bob");
    const aliceId = store.speakers[0].id;
    store.deleteSpeaker(aliceId);
    expect(store.speakers).toHaveLength(1);
    expect(store.speakers[0].name).toBe("Bob");
});

test("deleteSpeaker clears references and marks referencing segments dirty", () => {
    const store = useTranscriptStore();
    store.speakers = [
        { id: "spk_a", name: "Alice", color: "#000000" },
        { id: "spk_b", name: "Bob", color: "#111111" },
    ];
    store.segments = [
        {
            id: "1",
            speakerId: "spk_a",
            words: [
                { id: "w1", word: "hi", speakerId: "spk_a" },
                { id: "w2", word: "there", speakerId: "spk_b" },
            ],
        },
        {
            id: "2",
            speakerId: "spk_b",
            words: [{ id: "w3", word: "yo", speakerId: "spk_b" }],
        },
        {
            id: "3",
            speakerId: "spk_b",
            words: [{ id: "w4", word: "again", speakerId: "spk_a" }],
        },
    ] as any;
    store.deleteSpeaker("spk_a");

    // References to the deleted speaker are cleared.
    expect(store.segments[0].speakerId).toBeNull();
    expect(store.segments[0].words[0].speakerId).toBeNull();
    expect(store.segments[2].words[0].speakerId).toBeNull();

    // Segment 1 references spk_a directly; segment 3 via one of its words.
    expect(store.segments[0].dirty).toBe(true);
    expect(store.segments[1].dirty).toBeUndefined();
    expect(store.segments[2].dirty).toBe(true);

    // Untouched references stay intact.
    expect(store.segments[0].words[1].speakerId).toBe("spk_b");
    expect(store.segments[1].speakerId).toBe("spk_b");
});

test("deleteSpeaker throws when the speaker does not exist", () => {
    const store = useTranscriptStore();
    expect(() => store.deleteSpeaker("spk_ghost")).toThrow(
        "Speaker does not exist: spk_ghost",
    );
});

test("insertSegmentAfter inserts a new segment right after the given one", () => {
    const store = useTranscriptStore();
    store.segments = [
        { id: "a", start: 0, end: 5, text: "one", speakerId: null, words: [] },
        { id: "b", start: 7, end: 10, text: "two", speakerId: null, words: [] },
    ];

    store.insertSegmentAfter("new", "a");

    expect(store.segments).toHaveLength(3);
    expect(store.segments[0].id).toBe("a");
    expect(store.segments[2].id).toBe("b");
    expect(store.segments[1].text).toBe("new");
});

test("insertSegmentAfter spans the gap between the segment and its successor", () => {
    const store = useTranscriptStore();
    store.segments = [
        { id: "a", start: 0, end: 5, text: "one", speakerId: null, words: [] },
        { id: "b", start: 7, end: 10, text: "two", speakerId: null, words: [] },
    ];

    store.insertSegmentAfter("new", "a");

    expect(store.segments[1].start).toBe(5);
    expect(store.segments[1].end).toBe(7);
});

test("insertSegmentAfter gives the last segment a default 15s duration", () => {
    const store = useTranscriptStore();
    store.segments = [
        { id: "a", start: 0, end: 5, text: "one", speakerId: null, words: [] },
    ];

    store.insertSegmentAfter("new", "a");

    expect(store.segments[1].start).toBe(5);
    expect(store.segments[1].end).toBe(20);
});

test("insertSegmentAfter is a no-op for an unknown segment id", () => {
    const store = useTranscriptStore();
    store.segments = [
        { id: "a", start: 0, end: 5, text: "one", speakerId: null, words: [] },
    ];

    store.insertSegmentAfter("new", "ghost");

    expect(store.segments).toHaveLength(1);
});

test("mentionLabel resolves a word's mentionId to its mention label", () => {
    const store = useTranscriptStore();
    store.mentions = {
        men_1: { label: "PER", score: 1.0 },
        men_2: { label: "LOC", score: 0.8 },
    };

    expect(store.mentionLabel("men_1")).toBe("PER");
    expect(store.mentionLabel("men_2")).toBe("LOC");
});

test("mentionLabel returns null for missing or unknown mention ids", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "PER", score: 1.0 } };

    expect(store.mentionLabel(null)).toBeNull();
    expect(store.mentionLabel(undefined)).toBeNull();
    expect(store.mentionLabel("men_ghost")).toBeNull();
});

test("mention resolves a mentionId to its mention object", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.76 } };

    expect(store.mention("men_1")).toEqual({ label: "LOC", score: 0.76 });
});

test("mention returns null for missing or unknown mention ids", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.76 } };

    expect(store.mention(null)).toBeNull();
    expect(store.mention(undefined)).toBeNull();
    expect(store.mention("men_ghost")).toBeNull();
});

test("mentionText joins the words of a mention within a segment", () => {
    const store = useTranscriptStore();
    store.segments = [
        {
            id: "seg_1",
            words: [
                { id: "w1", word: "I", mentionId: null },
                { id: "w2", word: "visited", mentionId: null },
                { id: "w3", word: "New", mentionId: "men_1" },
                { id: "w4", word: "York", mentionId: "men_1" },
                { id: "w5", word: "today", mentionId: null },
            ],
        },
    ] as any;

    expect(store.mentionText(0, "men_1")).toBe("New York");
});

test("mentionText returns an empty string when nothing matches", () => {
    const store = useTranscriptStore();
    store.segments = [
        { id: "seg_1", words: [{ id: "w1", word: "hi", mentionId: null }] },
    ] as any;

    expect(store.mentionText(0, "men_ghost")).toBe("");
    expect(store.mentionText(0, null)).toBe("");
    expect(store.mentionText(9, "men_1")).toBe("");
});

test("removeMention unlinks the mention's words and drops the mention", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [
        {
            id: "seg_1",
            words: [
                { id: "w1", word: "in", mentionId: null },
                { id: "w2", word: "New", mentionId: "men_1" },
                { id: "w3", word: "York", mentionId: "men_1" },
            ],
        },
    ] as any;

    store.removeMention(0, "men_1");

    expect(store.mentions).toEqual({});
    expect(store.segments[0].words.map((w) => w.mentionId)).toEqual([
        null,
        null,
        null,
    ]);
    expect(store.segments[0].dirty).toBe(true);
});

test("removeMention leaves other segments and mentions untouched", () => {
    const store = useTranscriptStore();
    store.mentions = {
        men_1: { label: "LOC", score: 0.9 },
        men_2: { label: "PER", score: 0.8 },
    } as any;
    store.segments = [
        { id: "seg_1", words: [{ id: "w1", word: "York", mentionId: "men_1" }] },
        { id: "seg_2", words: [{ id: "w2", word: "Alice", mentionId: "men_2" }] },
    ] as any;

    store.removeMention(0, "men_1");

    expect(store.mentions).toEqual({ men_2: { label: "PER", score: 0.8 } });
    expect(store.segments[1].words[0].mentionId).toBe("men_2");
    expect(store.segments[1].dirty).toBeUndefined();
});

test("setMentionLabel updates the mention's label and marks the segment dirty", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [
        { id: "seg_1", words: [{ id: "w1", word: "York", mentionId: "men_1" }] },
    ] as any;

    store.setMentionLabel(0, "men_1", "PER");

    expect(store.mentions.men_1.label).toBe("PER");
    expect(store.segments[0].dirty).toBe(true);
});

test("setMentionLabel ignores an unknown mention", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [{ id: "seg_1", words: [] }] as any;

    store.setMentionLabel(0, "men_ghost", "PER");

    expect(store.mentions.men_1.label).toBe("LOC");
    expect(store.segments[0].dirty).toBeUndefined();
});

test("createMention adds a mention, links the word and marks the segment dirty", () => {
    const store = useTranscriptStore();
    store.mentions = {};
    store.segments = [
        {
            id: "seg_1",
            words: [{ id: "w1", word: "New", mentionId: null }],
        },
    ] as any;

    store.createMention(0, 0, "LOC");

    const ids = Object.keys(store.mentions);
    expect(ids).toHaveLength(1);
    expect(store.mentions[ids[0]]).toEqual({ label: "LOC", score: 1 });
    expect(store.segments[0].words[0].mentionId).toBe(ids[0]);
    expect(store.segments[0].dirty).toBe(true);
});

test("createMention ignores an out-of-range word", () => {
    const store = useTranscriptStore();
    store.mentions = {};
    store.segments = [{ id: "seg_1", words: [] }] as any;

    store.createMention(0, 5, "LOC");

    expect(store.mentions).toEqual({});
    expect(store.segments[0].dirty).toBeUndefined();
});

test("extendMention absorbs the word to the left of the span", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [
        {
            id: "seg_1",
            words: [
                { id: "w0", word: "in", mentionId: null },
                { id: "w1", word: "New", mentionId: "men_1" },
                { id: "w2", word: "York", mentionId: "men_1" },
            ],
        },
    ] as any;

    store.extendMention(0, "men_1", "left");

    expect(store.segments[0].words[0].mentionId).toBe("men_1");
    expect(store.segments[0].dirty).toBe(true);
});

test("extendMention absorbs the word to the right of the span", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [
        {
            id: "seg_1",
            words: [
                { id: "w1", word: "New", mentionId: "men_1" },
                { id: "w2", word: "York", mentionId: "men_1" },
                { id: "w3", word: "City", mentionId: null },
            ],
        },
    ] as any;

    store.extendMention(0, "men_1", "right");

    expect(store.segments[0].words[2].mentionId).toBe("men_1");
    expect(store.segments[0].dirty).toBe(true);
});

test("extendMention does nothing at a segment boundary", () => {
    const store = useTranscriptStore();
    store.mentions = { men_1: { label: "LOC", score: 0.9 } } as any;
    store.segments = [
        { id: "seg_1", words: [{ id: "w0", word: "York", mentionId: "men_1" }] },
    ] as any;

    store.extendMention(0, "men_1", "left");

    expect(store.segments[0].dirty).toBeUndefined();
});

test("extendMention does not steal a word from another mention", () => {
    const store = useTranscriptStore();
    store.mentions = {
        men_1: { label: "LOC", score: 0.9 },
        men_2: { label: "PER", score: 0.8 },
    } as any;
    store.segments = [
        {
            id: "seg_1",
            words: [
                { id: "w0", word: "Alice", mentionId: "men_2" },
                { id: "w1", word: "York", mentionId: "men_1" },
            ],
        },
    ] as any;

    store.extendMention(0, "men_1", "left");

    expect(store.segments[0].words[0].mentionId).toBe("men_2");
    expect(store.segments[0].dirty).toBeUndefined();
});
