import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test } from "vitest";
import TranscriptWord from "./transcript_word.vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptWord as Word } from "./types";

beforeEach(() => {
    setActivePinia(createPinia());
});

function word(overrides: Partial<Word> = {}): Word {
    return {
        id: "wrd_1",
        start: 1,
        end: 2,
        word: "Acme",
        score: 0.9,
        ...overrides,
    };
}

function mountWord(w: Word, props: Record<string, unknown> = {}) {
    return mount(TranscriptWord, {
        props: { segmentIndex: 0, index: 0, word: w, ...props },
        global: { mocks: { $t: (key: string) => key } },
    });
}

describe("TranscriptWord redaction marking", () => {
    test("marks a word that carries a redactionId", () => {
        const wrapper = mountWord(word({ redactionId: "red_1" }));

        expect(wrapper.classes()).toContain("transcript-word--redacted");
    });

    test("does not mark a word without a redactionId", () => {
        expect(mountWord(word()).classes()).not.toContain(
            "transcript-word--redacted",
        );
        expect(mountWord(word({ redactionId: null })).classes()).not.toContain(
            "transcript-word--redacted",
        );
    });

    test("marks the word whether or not entity display is on", () => {
        const store = useTranscriptStore();
        store.mentions = { men_1: { label: "ORG", score: 0.9, entityId: null } };
        const w = word({ redactionId: "red_1", mentionId: "men_1" });

        const shown = mountWord(w, { showEntities: true });
        expect(shown.classes()).toContain("transcript-word--redacted");
        // The redaction composes with the entity fill rather than replacing it.
        expect(shown.classes()).toContain("transcript-word--entity");

        const hidden = mountWord(w, { showEntities: false });
        expect(hidden.classes()).toContain("transcript-word--redacted");
        expect(hidden.classes()).not.toContain("transcript-word--entity");
    });
});
