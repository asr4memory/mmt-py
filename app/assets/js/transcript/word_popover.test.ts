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

        // The mention section is present but has no entity details yet.
        expect(wrapper.findAll(".popup__section")).toHaveLength(2);
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
        store.mentions = { men_1: { label: "LOC", score: 0.76 } };
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
        store.mentions = { men_1: { label: "LOC", score: 0.76 } };
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
});
