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
    test("renders the three action buttons", () => {
        const wrapper = mountPopover();

        const buttons = wrapper.findAll("button");
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
});
