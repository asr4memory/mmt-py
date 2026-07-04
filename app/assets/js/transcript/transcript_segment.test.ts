import { describe, test, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import TranscriptSegment from "./transcript_segment.vue";
import TranscriptWord from "./transcript_word.vue";
import type { TranscriptSegment as Segment, TranscriptWord as Word } from "./types";

beforeEach(() => {
    setActivePinia(createPinia());
});

function word(id: string, mentionId: string | null): Word {
    return { id, start: 0, end: 1, word: id, score: 1, mentionId };
}

function mountSegment(words: Word[]) {
    const segment: Segment = {
        id: "seg_1",
        start: 0,
        end: 10,
        text: words.map((w) => w.word).join(" "),
        speakerId: null,
        words,
    };
    return mount(TranscriptSegment, {
        props: { index: 0, segment },
        global: { mocks: { $t: (key: string) => key } },
    });
}

function mentionFlags(wrapper: ReturnType<typeof mountSegment>) {
    return wrapper.findAllComponents(TranscriptWord).map((w) => ({
        start: w.props("isMentionStart") ?? false,
        end: w.props("isMentionEnd") ?? false,
    }));
}

describe("TranscriptSegment mention boundaries", () => {
    test("words without a mention are neither start nor end", () => {
        const wrapper = mountSegment([word("a", null), word("b", null)]);
        expect(mentionFlags(wrapper)).toEqual([
            { start: false, end: false },
            { start: false, end: false },
        ]);
    });

    test("a multi-word mention marks its first and last word", () => {
        const wrapper = mountSegment([
            word("a", null),
            word("b", "m1"),
            word("c", "m1"),
            word("d", null),
        ]);
        expect(mentionFlags(wrapper)).toEqual([
            { start: false, end: false },
            { start: true, end: false },
            { start: false, end: true },
            { start: false, end: false },
        ]);
    });

    test("a single-word mention is both start and end", () => {
        const wrapper = mountSegment([word("a", null), word("b", "m1")]);
        expect(mentionFlags(wrapper)).toEqual([
            { start: false, end: false },
            { start: true, end: true },
        ]);
    });

    test("adjacent mentions with different ids are separated", () => {
        const wrapper = mountSegment([word("a", "m1"), word("b", "m2")]);
        expect(mentionFlags(wrapper)).toEqual([
            { start: true, end: true },
            { start: true, end: true },
        ]);
    });
});
