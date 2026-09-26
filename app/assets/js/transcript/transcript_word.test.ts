import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";
import { useMediaStore } from "./media_store";
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
    const { attachTo, ...wordProps } = props;
    return mount(TranscriptWord, {
        props: { segmentIndex: 0, index: 0, word: w, ...wordProps },
        global: { mocks: { $t: (key: string) => key } },
        ...(attachTo ? { attachTo: attachTo as HTMLElement } : {}),
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
        store.mentions = {
            men_1: { type: "ORG", score: 0.9, entityId: null },
        };
        const w = word({ redactionId: "red_1", mentionId: "men_1" });

        const shown = mountWord(w, { visibleEntityTypes: ["ORG"] });
        expect(shown.classes()).toContain("transcript-word--redacted");
        // The redaction composes with the entity fill rather than replacing it.
        expect(shown.classes()).toContain("transcript-word--entity");

        const hidden = mountWord(w, { visibleEntityTypes: [] });
        expect(hidden.classes()).toContain("transcript-word--redacted");
        expect(hidden.classes()).not.toContain("transcript-word--entity");
    });
});

describe("TranscriptWord entity type filter", () => {
    function mentionWord(type: string) {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { type, score: 0.9, entityId: null },
        };
        return word({ mentionId: "men_1" });
    }

    test("styles a word whose type is among the visible types", () => {
        const wrapper = mountWord(mentionWord("PER"), {
            visibleEntityTypes: ["PER", "LOC"],
        });

        expect(wrapper.classes()).toContain("transcript-word--entity");
        expect(wrapper.attributes("data-entity")).toBe("PER");
    });

    test("drops the styling for a type that is not among the visible types", () => {
        const wrapper = mountWord(mentionWord("ORG"), {
            visibleEntityTypes: ["PER", "LOC"],
        });

        expect(wrapper.classes()).not.toContain("transcript-word--entity");
        expect(wrapper.attributes("data-entity")).toBeUndefined();
    });

    test("drops the styling for every type when nothing is visible", () => {
        const wrapper = mountWord(mentionWord("PER"), {
            visibleEntityTypes: [],
        });

        expect(wrapper.classes()).not.toContain("transcript-word--entity");
    });
});

describe("TranscriptWord playback", () => {
    test("plays from the start of the word on shift-click", async () => {
        const media = useMediaStore();
        const playFrom = vi.spyOn(media, "playFrom");
        const wrapper = mountWord(word({ start: 12.5 }));

        await wrapper.trigger("click", { shiftKey: true });

        expect(playFrom).toHaveBeenCalledWith(12.5);
    });

    test("does not play on a click without the shift key", async () => {
        const media = useMediaStore();
        const playFrom = vi.spyOn(media, "playFrom");
        const wrapper = mountWord(word({ start: 12.5 }));

        await wrapper.trigger("click");

        expect(playFrom).not.toHaveBeenCalled();
    });
});

describe("TranscriptWord focus request", () => {
    test("opens the input with its text selected when the store asks for it", async () => {
        const store = useTranscriptStore();
        store.focusWordId = "wrd_1";
        const select = vi.spyOn(HTMLInputElement.prototype, "select");

        const wrapper = mountWord(word({ id: "wrd_1", word: "…" }), {
            attachTo: document.body,
        });
        await nextTick();
        await nextTick();

        const input = wrapper.find("input.transcript-word__input");
        expect(input.exists()).toBe(true);
        expect(document.activeElement).toBe(input.element);
        expect(select).toHaveBeenCalled();
        expect(store.focusWordId).toBeNull();
    });

    test("leaves a word alone when the request names another word", async () => {
        const store = useTranscriptStore();
        store.focusWordId = "wrd_2";

        const wrapper = mountWord(word({ id: "wrd_1" }));
        await nextTick();

        expect(wrapper.find("input.transcript-word__input").exists()).toBe(
            false,
        );
        expect(store.focusWordId).toBe("wrd_2");
    });
});
