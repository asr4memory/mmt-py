import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";
import { useTranscriptStore } from "./transcript_store";
import type { TranscriptWord } from "./types";
import WordPopover from "./word_popover.vue";

// Floating UI computes real layout, which jsdom cannot provide; the component's
// behavior is independent of where the popover ends up on screen.
vi.mock("@floating-ui/vue", () => ({
    useFloating: () => ({ floatingStyles: ref({}) }),
    autoUpdate: () => () => {},
    offset: () => ({}),
    flip: () => ({}),
    shift: () => ({}),
}));

const WORD: TranscriptWord = {
    id: "wrd_1",
    start: 1.5,
    end: 2.25,
    word: "hello",
    score: 0.92,
    speakerId: "spk_a",
};

function mountPopover(word: TranscriptWord = WORD) {
    return mount(WordPopover, {
        props: {
            segmentIndex: 3,
            index: 7,
            word,
            reference: document.createElement("span"),
        },
        global: {
            mocks: { $t: (key: string) => key },
            stubs: { teleport: true },
        },
    });
}

beforeEach(() => {
    setActivePinia(createPinia());
});

describe("WordPopover", () => {
    test("renders the three word action buttons", () => {
        const wrapper = mountPopover();

        const buttons = wrapper.findAll(".popup__section")[0].findAll("button");
        expect(buttons).toHaveLength(3);
        expect(buttons.map((b) => b.attributes("title"))).toEqual([
            "add_word_left",
            "add_word_right",
            "remove_word",
        ]);
    });

    test("renders the score", () => {
        const wrapper = mountPopover();

        expect(wrapper.text()).toContain("confidence");
    });

    test("add-left button inserts a word and closes", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "insertLeft").mockImplementation(() => {});

        const wrapper = mountPopover();
        await wrapper.find("[title='add_word_left']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("add-right button inserts a word and closes", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "insertRight").mockImplementation(() => {});

        const wrapper = mountPopover();
        await wrapper.find("[title='add_word_right']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("remove button deletes the word and closes", async () => {
        const store = useTranscriptStore();
        const spy = vi.spyOn(store, "deleteWord").mockImplementation(() => {});

        const wrapper = mountPopover();
        await wrapper.find("[title='remove_word']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("emits close when Escape is pressed", async () => {
        const wrapper = mountPopover();

        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("emits close on an outside pointer press", async () => {
        const wrapper = mountPopover();

        document.body.dispatchEvent(
            new PointerEvent("pointerdown", { bubbles: true }),
        );
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("does not close when pressing inside the popover", async () => {
        const wrapper = mountPopover();

        const popover = wrapper.find(".popup").element;
        popover.dispatchEvent(
            new PointerEvent("pointerdown", { bubbles: true }),
        );
        await wrapper.vm.$nextTick();

        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("shows an empty mention section with a create action when unlinked", () => {
        const wrapper = mountPopover();

        // The word, mention and redaction sections are present, but the
        // mention section has no entity details yet.
        expect(wrapper.findAll(".popup__section")).toHaveLength(3);
        expect(wrapper.find(".popup__select").exists()).toBe(false);
        expect(wrapper.text()).not.toContain("entity_type");
        expect(wrapper.find("[title='set_as_mention']").exists()).toBe(true);
    });

    test("set-as-mention creates a mention for the word and stays open", async () => {
        const store = useTranscriptStore();
        const spy = vi
            .spyOn(store, "createMention")
            .mockImplementation(() => {});

        const wrapper = mountPopover();
        await wrapper.find("[title='set_as_mention']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7, "PER");
        expect(wrapper.emitted("close")).toBeUndefined();
    });

    function mountMentionPopover() {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { label: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_a", word: "New", mentionId: "men_1" },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        return { store, wrapper: mountPopover(word) };
    }

    test("shows the entity type and full mention text for a mention word", () => {
        const { wrapper } = mountMentionPopover();

        // Two sections: the word, then the mention.
        const titles = wrapper.findAll(".popup__title");
        expect(titles).toHaveLength(2);
        // The full mention surface form as a heading, not just the clicked word.
        expect(titles[1].text()).toBe("New York");
        expect(wrapper.text()).toContain("entity_type");

        // The type is an editable select preset to the mention's label.
        const select = wrapper.find(".popup__select");
        expect((select.element as HTMLSelectElement).value).toBe("LOC");
        expect(select.findAll("option").map((o) => o.attributes("value"))).toEqual([
            "PER",
            "LOC",
            "ORG",
            "DATE",
        ]);
    });

    test("changing the type select relabels the mention", async () => {
        const { store, wrapper } = mountMentionPopover();
        const spy = vi
            .spyOn(store, "setMentionLabel")
            .mockImplementation(() => {});

        await wrapper.find(".popup__select").setValue("PER");

        expect(spy).toHaveBeenCalledWith(3, "men_1", "PER");
        // Editing the type keeps the popover open.
        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("remove-mention button removes the whole mention and closes", async () => {
        const { store, wrapper } = mountMentionPopover();
        const spy = vi
            .spyOn(store, "removeMention")
            .mockImplementation(() => {});

        await wrapper.find("[title='remove_mention']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, "men_1");
        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    test("disables extend when the span already fills the segment", () => {
        // mountMentionPopover's mention covers every word in the segment.
        const { wrapper } = mountMentionPopover();

        expect(
            wrapper.find("[title='extend_mention_left']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='extend_mention_right']").attributes("disabled"),
        ).toBeDefined();
    });

    // Mention "New York" flanked by a free word on each side.
    function mountMentionWithNeighbours() {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { label: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "in", mentionId: null },
                    { id: "w_a", word: "New", mentionId: "men_1" },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                    { id: "w_y", word: "today", mentionId: null },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        return { store, wrapper: mountPopover(word) };
    }

    test("extend buttons grow the mention and keep the popover open", async () => {
        const { store, wrapper } = mountMentionWithNeighbours();
        const spy = vi
            .spyOn(store, "extendMention")
            .mockImplementation(() => {});

        const left = wrapper.find("[title='extend_mention_left']");
        const right = wrapper.find("[title='extend_mention_right']");
        expect(left.attributes("disabled")).toBeUndefined();
        expect(right.attributes("disabled")).toBeUndefined();

        await left.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "left");

        await right.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "right");

        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("reduce buttons trim the span and keep the popover open", async () => {
        const { store, wrapper } = mountMentionWithNeighbours();
        const spy = vi
            .spyOn(store, "reduceMention")
            .mockImplementation(() => {});

        await wrapper.find("[title='reduce_mention_left']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "left");

        await wrapper.find("[title='reduce_mention_right']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "men_1", "right");

        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("disables reduce for a single-word mention", () => {
        const store = useTranscriptStore();
        store.mentions = {
            men_1: { label: "LOC", score: 0.76, entityId: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "in", mentionId: null },
                    { id: "w_b", word: "York", mentionId: "men_1" },
                    { id: "w_y", word: "today", mentionId: null },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "York",
            score: 0.9,
            mentionId: "men_1",
        };
        const wrapper = mountPopover(word);

        expect(
            wrapper.find("[title='reduce_mention_left']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='reduce_mention_right']").attributes("disabled"),
        ).toBeDefined();
        // But a single-word mention flanked by free words can still grow.
        expect(
            wrapper.find("[title='extend_mention_left']").attributes("disabled"),
        ).toBeUndefined();
    });
});

describe("WordPopover redaction section", () => {
    // Redaction "at Acme" with a free word on each side, in segment 3.
    function mountRedactionPopover(reason: string | null = null) {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "I", redactionId: null },
                    { id: "w_a", word: "at", redactionId: "red_1" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                    { id: "w_y", word: "today", redactionId: null },
                ],
            },
        ] as any;

        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        return { store, wrapper: mountPopover(word) };
    }

    test("shows the empty state with a redact action for an unredacted word", () => {
        const wrapper = mountPopover();

        expect(wrapper.text()).toContain("no_redaction");
        expect(wrapper.find("[title='set_as_redaction']").exists()).toBe(true);
        expect(wrapper.find(".popup__input").exists()).toBe(false);
        expect(wrapper.find("[title='remove_redaction']").exists()).toBe(false);
    });

    test("redact button creates a redaction for the word and stays open", async () => {
        const store = useTranscriptStore();
        const spy = vi
            .spyOn(store, "createRedaction")
            .mockImplementation(() => "red_new");

        const wrapper = mountPopover();
        await wrapper.find("[title='set_as_redaction']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, 7);
        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("shows the surface text of the whole run for a redacted word", () => {
        const { wrapper } = mountRedactionPopover();

        // Three sections: the word, the (empty) mention, then the redaction.
        expect(wrapper.findAll(".popup__section")).toHaveLength(3);
        const titles = wrapper.findAll(".popup__title");
        // The word's own title, then the redaction's full surface form.
        expect(titles).toHaveLength(2);
        expect(titles[1].text()).toBe("at Acme");
        expect(wrapper.text()).not.toContain("no_redaction");
    });

    test("shows the stored reason in the reason input", () => {
        const { wrapper } = mountRedactionPopover("employer");

        const input = wrapper.find(".popup__input");
        expect((input.element as HTMLInputElement).value).toBe("employer");
    });

    test("shows an empty reason input when the redaction carries none", () => {
        const { wrapper } = mountRedactionPopover(null);

        expect(
            (wrapper.find(".popup__input").element as HTMLInputElement).value,
        ).toBe("");
    });

    test("typing a reason records it and keeps the popover open", async () => {
        const { store, wrapper } = mountRedactionPopover();
        const spy = vi
            .spyOn(store, "setRedactionReason")
            .mockImplementation(() => {});

        await wrapper.find(".popup__input").setValue("employer");

        expect(spy).toHaveBeenCalledWith("red_1", "employer");
        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("extend buttons grow the redaction and keep the popover open", async () => {
        const { store, wrapper } = mountRedactionPopover();
        const spy = vi
            .spyOn(store, "extendRedaction")
            .mockImplementation(() => {});

        const left = wrapper.find("[title='extend_redaction_left']");
        const right = wrapper.find("[title='extend_redaction_right']");
        expect(left.attributes("disabled")).toBeUndefined();
        expect(right.attributes("disabled")).toBeUndefined();

        await left.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "left");

        await right.trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "right");

        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("reduce buttons shorten the run and keep the popover open", async () => {
        const { store, wrapper } = mountRedactionPopover();
        const spy = vi
            .spyOn(store, "reduceRedaction")
            .mockImplementation(() => {});

        await wrapper.find("[title='reduce_redaction_left']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "left");

        await wrapper.find("[title='reduce_redaction_right']").trigger("click");
        expect(spy).toHaveBeenCalledWith(3, "red_1", "right");

        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("remove button removes the whole redaction and keeps the popover open", async () => {
        const { store, wrapper } = mountRedactionPopover("employer");
        const spy = vi
            .spyOn(store, "removeRedaction")
            .mockImplementation(() => {});

        await wrapper.find("[title='remove_redaction']").trigger("click");

        expect(spy).toHaveBeenCalledWith(3, "red_1");
        // The section returns to its empty state rather than closing.
        expect(wrapper.emitted("close")).toBeUndefined();
    });

    test("disables extend when the run already fills the segment", () => {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason: null, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_a", word: "at", redactionId: "red_1" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPopover(word);

        expect(
            wrapper.find("[title='extend_redaction_left']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='extend_redaction_right']").attributes("disabled"),
        ).toBeDefined();
    });

    test("disables extend onto a word held by another redaction", () => {
        const store = useTranscriptStore();
        store.redactions = {
            red_1: { reason: null, start: null, end: null },
            red_2: { reason: null, start: null, end: null },
        };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "Berlin", redactionId: "red_2" },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                    { id: "w_y", word: "today", redactionId: null },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPopover(word);

        expect(
            wrapper.find("[title='extend_redaction_left']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='extend_redaction_right']").attributes("disabled"),
        ).toBeUndefined();
    });

    test("disables reduce for a single-word redaction", () => {
        const store = useTranscriptStore();
        store.redactions = { red_1: { reason: null, start: null, end: null } };
        store.segments = [
            { id: "seg_0", words: [] },
            { id: "seg_1", words: [] },
            { id: "seg_2", words: [] },
            {
                id: "seg_3",
                words: [
                    { id: "w_x", word: "at", redactionId: null },
                    { id: "w_b", word: "Acme", redactionId: "red_1" },
                ],
            },
        ] as any;
        const word: TranscriptWord = {
            id: "w_b",
            start: 1,
            end: 2,
            word: "Acme",
            score: 0.9,
            redactionId: "red_1",
        };
        const wrapper = mountPopover(word);

        expect(
            wrapper.find("[title='reduce_redaction_left']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='reduce_redaction_right']").attributes("disabled"),
        ).toBeDefined();
        expect(
            wrapper.find("[title='extend_redaction_left']").attributes("disabled"),
        ).toBeUndefined();
    });
});
